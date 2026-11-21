"""LLM understanding: one transcript sentence -> a validated JSON patch for the visit record.

    understand("thoda khoon aa raha tha kal, ab nahi", "anc", {})
    -> {"ok": True, "provider": "groq", "ms": 640, "fields": {...}, "evidence": {...},
        "unsure": [...], "correction_of": [...], "danger_signs": [...], "off_topic": False}

Groq first (JSON mode, 3 s timeout), then local Ollama (LOCAL_MODEL). If both fail it returns
{"ok": False, "error": ...} and the visit carries on with rules only. The LLM never writes speech;
everything it returns is validated here and anything that doesn't fit the schema is dropped.
It is synchronous: callers that must not block (danger alerts) run it in a thread.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path

import httpx
from dotenv import load_dotenv

from asha.danger import VISIT_GROUPS
from asha.text import DATA

log = logging.getLogger("asha.llm")

ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = ROOT / "prompts" / "understand.md"
load_dotenv(ROOT / ".env")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"   # llama-3.3-70b-versatile is no longer offered
GROQ_TIMEOUT_S = 3.0
OLLAMA_TIMEOUT_S = 8.0
MAX_TOKENS = 600

SUBJECTS = {"mother", "newborn", "child"}
NUMBER_FIELDS = {"weight_kg", "bp_systolic", "bp_diastolic", "hb", "breaths_per_min"}
LIST_FIELDS = {"vaccines_given", "vaccines_due"}
FIELDS = NUMBER_FIELDS | LIST_FIELDS | {"subject", "temperature", "ifa_taking", "next_visit_text"}
SIGN_STATUSES = {"present", "absent", "past"}

_client: httpx.Client | None = None


# ---------- prompt ----------

@lru_cache(maxsize=1)
def _signs() -> list[dict]:
    return json.loads((DATA / "danger_signs.json").read_text(encoding="utf-8"))


def allowed_sign_ids(visit_type: str) -> set[str]:
    groups = VISIT_GROUPS.get(visit_type)
    return {s["id"] for s in _signs() if groups is None or s["group"] in groups}


def _short_wording(official: str) -> str:
    """'"Bleeding from vagina" (M6); "Bleeding during pregnancy" (MCP)' -> 'Bleeding from vagina / ...'"""
    quoted = list(dict.fromkeys(re.findall(r'"([^"]+)"', official)))
    return " / ".join(quoted) if quoted else official


@lru_cache(maxsize=8)
def system_prompt(visit_type: str) -> str:
    ids = allowed_sign_ids(visit_type)
    lines = [f"{s['id']}: {_short_wording(s['official_wording'])}" for s in _signs() if s["id"] in ids]
    return PROMPT_FILE.read_text(encoding="utf-8").replace("{DANGER_SIGN_LIST}", "\n".join(lines))


def user_message(transcript: str, visit_type: str, current_record: dict) -> str:
    return (f"VISIT_TYPE: {visit_type}\n"
            f"CURRENT_RECORD: {json.dumps(current_record, ensure_ascii=False, default=str)}\n"
            f"SENTENCE: {transcript}")


# ---------- validation ----------

def _number(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, str):
        try:
            v = float(v.strip())
        except ValueError:
            return None
    if isinstance(v, (int, float)) and v > 0:
        return int(v) if float(v).is_integer() else float(v)
    return None


def _field(name: str, v):
    """Return the cleaned value, or None if it doesn't fit the schema."""
    if name in NUMBER_FIELDS:
        return _number(v)
    if name == "subject":
        return v if v in SUBJECTS else None
    if name == "ifa_taking":
        return v if isinstance(v, bool) else None
    if name == "next_visit_text":
        return v.strip() if isinstance(v, str) and v.strip() else None
    if name in LIST_FIELDS:
        if not isinstance(v, list):
            return None
        items = [x.strip() for x in v if isinstance(x, str) and x.strip()]
        return items or None
    if name == "temperature":
        if not isinstance(v, dict):
            return None
        value, unit = _number(v.get("value")), str(v.get("unit", "")).upper()
        return {"value": value, "unit": unit} if value is not None and unit in ("F", "C") else None
    return None


def _strings(v) -> list[str]:
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def validate(raw: dict, visit_type: str) -> dict:
    """Keep only what fits the schema in prompts/understand.md; drop the rest (logged)."""
    dropped = []
    fields = {}
    raw_fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    for name, v in raw_fields.items():
        clean = _field(name, v) if name in FIELDS else None
        if clean is None:
            dropped.append(f"fields.{name}")
        else:
            fields[name] = clean

    evidence = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
    evidence = {k: v for k, v in evidence.items() if k in fields and isinstance(v, str)}

    allowed = allowed_sign_ids(visit_type)
    signs: dict[str, dict] = {}
    for s in raw.get("danger_signs") or []:
        if not isinstance(s, dict) or s.get("id") not in allowed or s.get("status") not in SIGN_STATUSES:
            dropped.append(f"danger_signs.{s.get('id') if isinstance(s, dict) else s}")
            continue
        sign = {"id": s["id"], "status": s["status"],
                "evidence": s["evidence"] if isinstance(s.get("evidence"), str) else ""}
        # Safety: if the same sign comes twice, a present/past reading beats an absent one.
        if s["id"] not in signs or signs[s["id"]]["status"] == "absent":
            signs[s["id"]] = sign

    if dropped:
        log.info("llm output dropped: %s", ", ".join(dropped))
    return {
        "fields": fields,
        "evidence": evidence,
        "unsure": [f for f in _strings(raw.get("unsure")) if f in FIELDS],
        "correction_of": [f for f in _strings(raw.get("correction_of")) if f in FIELDS],
        "danger_signs": list(signs.values()),
        "off_topic": raw.get("off_topic") is True,
    }


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("LLM returned JSON that is not an object")
    return data


# ---------- providers ----------

def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client()
    return _client


def _messages(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_groq(system: str, user: str) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    model = os.getenv("GROQ_MODEL", GROQ_DEFAULT_MODEL)
    body = {"model": model, "messages": _messages(system, user),
            "response_format": {"type": "json_object"}, "temperature": 0, "max_tokens": MAX_TOKENS}
    if model.startswith("openai/gpt-oss"):          # reasoning model: keep its thinking short for speed
        body["reasoning_effort"] = os.getenv("GROQ_REASONING", "low")
    r = _http().post(GROQ_URL, timeout=GROQ_TIMEOUT_S, headers={"Authorization": f"Bearer {key}"}, json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_ollama(system: str, user: str) -> str:
    model = os.getenv("LOCAL_MODEL")
    if not model:
        raise RuntimeError("LOCAL_MODEL not set")
    url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    r = _http().post(f"{url}/api/chat", timeout=OLLAMA_TIMEOUT_S,
                     json={"model": model, "messages": _messages(system, user), "format": "json",
                           "stream": False, "keep_alive": "30m",
                           "options": {"temperature": 0, "num_predict": MAX_TOKENS}})
    r.raise_for_status()
    return r.json()["message"]["content"]


PROVIDERS = ("groq", "ollama")      # tried in this order


def understand(transcript: str, visit_type: str, current_record: dict) -> dict:
    system = system_prompt(visit_type)
    user = user_message(transcript, visit_type, current_record)
    calls = {"groq": call_groq, "ollama": call_ollama}
    errors = []
    for name in PROVIDERS:
        call = calls[name]
        t0 = time.perf_counter()
        try:
            result = validate(parse_json(call(system, user)), visit_type)
        except Exception as e:  # any provider failure -> try the next one
            # Log the exception type and message only: never the request (it may hold the key header).
            errors.append(f"{name}: {type(e).__name__}: {e}")
            log.warning("llm %s failed: %s", name, errors[-1])
            continue
        return {"ok": True, "provider": name, "ms": round((time.perf_counter() - t0) * 1000), **result}
    return {"ok": False, "error": "; ".join(errors)}
