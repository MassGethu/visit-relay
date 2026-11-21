"""One home visit, turn by turn: the glue between the modules.

    visit = Visit("hbnc", subject="newborn", lang="hi")
    visit.start()                       -> disclosure (always first)
    visit.hear(transcript, "hi-IN")     -> lines to speak now (danger alerts first)
    visit.readback()                    -> one choice question and/or one safety turn, or the summary
    visit.hear("record pakka")          -> saved, with a 5-second undo
    visit.events()                      -> browser events since the last call (record, alert, ...)

Numbers and dates come from the rules (numbers.py, dates.py). Every line returned is
already guarded and ready for TTS.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from .concern import carries_content, is_flag_request, is_worry
from .correction import apply_correction, is_commit, is_undo
from .danger import DangerChecker, sign_label
from .dates import resolve
from .numbers import extract_measurements
from .readback import Doubt, find_doubts, plan
from .speak import FIELD_NAMES, Speaker, spoken_sign
from .text import tokens

DATE_CUES = {"visit", "aana", "aaungi", "aayegi", "milenge", "barteeni", "bartini", "ಬರ್ತೀನಿ", "tareekh",
             "taareekhu", "agla", "agle", "mundina", "naale", "kal", "parson"}
RULE_FIELDS = ("weight_kg", "hb", "bp", "temperature", "breaths_per_min")
# LLM schema name -> record name (readback.py uses "vaccinations_*")
LLM_FIELDS = {"weight_kg": "weight_kg", "hb": "hb", "breaths_per_min": "breaths_per_min",
              "ifa_taking": "ifa_taking", "vaccines_given": "vaccinations_given",
              "vaccines_due": "vaccinations_due", "next_visit_text": "next_visit_text"}
DISCREET_WORDS = {"dheere", "dhire", "dheere-dheere", "धीरे", "ಮೆಲ್ಲಗೆ", "quietly"}
DISCREET_MAX_WORDS = 3                # longer sentences with "dheere" are content, not a command
# Never read aloud in discreet mode (the screen still shows them). Danger signs are always read.
SENSITIVE_FIELDS = {"family_planning", "contraception", "pregnancy_loss", "abortion",
                    "miscarriage", "stillbirth"}
LLM_WAIT_S = 15.0                    # upper bound; llm.py's own timeouts are 3 s + 8 s

log = logging.getLogger("asha.visit")
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def jsonable(v):
    """Record values -> JSON for the browser: dates as ISO strings, tuples as lists."""
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, tuple):
        return [jsonable(x) for x in v]
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    return v


@dataclass
class Visit:
    visit_type: str
    subject: str = "mother"           # whose numbers: "mother" | "newborn" | "child"
    lang: str = "hi"
    today: dt.date = field(default_factory=dt.date.today)
    tested_languages: tuple = ("hi", "en")
    use_llm: bool = True              # False: rules only (tests, text demo)
    understand: Callable[[str, str, dict], dict] | None = None   # default: llm.understand
    clock: Callable[[], float] = time.monotonic                  # for the 5-second undo
    beneficiary_id: str = ""
    use_store: bool = True            # False: nothing written to disk (tests, text demo)
    store: Any = None                 # default: store.default_store() (encrypted SQLite)

    def __post_init__(self):
        self.danger = DangerChecker(self.visit_type, self.tested_languages)
        self.speaker = Speaker(self.lang)
        self.record: dict = {}
        self.evidence: dict[str, str] = {}      # field -> her words
        self.extra_doubts: list[Doubt] = []
        self.alerted: list[str] = []
        self.saved = False
        self.saved_at: float | None = None
        self.discreet = False
        self._events: list[dict] = []
        self._unspoken: list[str] = []          # lines found after hear() returned (LLM alerts)
        self._pending: list[tuple[Future, str, int, set[str]]] = []
        self.transcript: list[dict] = []        # everything she said, with time (saved encrypted)
        self.flags: list[dict] = []             # every danger flag: sign, quote, time, rules or llm
        self.visit_id: int | None = None
        if self.use_store and self.store is None:
            from store import default_store     # lazy: rules-only visits never touch the disk
            self.store = default_store()
        if self.use_llm and self.understand is None:
            from llm import understand          # lazy: rules-only visits never touch the network
            self.understand = understand

    # ---------- contract with app.py ----------

    def start(self) -> list[str]:
        return [self.speaker.say("disclosure")]

    def hear(self, text: str, language_code: str | None = None) -> list[str]:
        language_code = language_code or f"{self.lang}-IN"
        self.transcript.append({"at": now(), "text": text, "lang": language_code})
        if self.saved:
            if is_undo(text, self.clock() - self.saved_at):
                self.saved, self.saved_at = False, None
                if self.store and self.visit_id is not None:
                    self.store.mark_undone(self.visit_id, now())
                self.visit_id = None
                self._events.append({"type": "undo"})
                return [self.speaker.say("undone")]
            log.info("visit already saved; ignoring: %r", text)
            return []
        if is_commit(text):
            self._drain(wait=True)              # nothing the LLM found may be lost by saving
            return self._take_unspoken() + self._save()
        words = [t.text for t in tokens(text)]
        if len(words) <= DISCREET_MAX_WORDS and set(words) & DISCREET_WORDS:
            self.discreet = True
            self._events.append({"type": "discreet", "on": True})
            return self._take_unspoken() + [self.speaker.say("discreet_on")]
        flag = is_flag_request(words)
        if flag and not carries_content(words):     # "ANM ko batao": flag the concern she just said
            return self._take_unspoken() + [self._flag_last_concern()]
        self._drain(wait=False)
        llm_job = None
        if self.use_llm:                        # start first so it runs while the rules work
            llm_job = _POOL.submit(self.understand, text, self.visit_type, jsonable(
                {k: v for k, v in self.record.items() if k != "worker_concerns"}))   # not LLM input
        new = self.danger.add_utterance(text, language_code)
        m = extract_measurements(text, self.subject)
        changed = False
        for key in RULE_FIELDS:
            if key in m:
                self._set(key, m[key], text)
                changed = True
        if llm_job:
            self._pending.append((llm_job, text, len(self.danger.utterances) - 1,
                                  {k for k in RULE_FIELDS if k in m}))
        for f, v, reason in m["doubts"]:
            if reason != "outside plausible range":     # range doubts are found again by readback
                self.extra_doubts.append(Doubt(f, v, "approximate"))
        new += self.danger.add_vitals(m)
        if set(text.lower().split()) & DATE_CUES:
            r = resolve(text, self.today)
            if r and r.kind == "date":
                self._set("next_visit_date", r.value, text)
                changed = True
                if r.confirm:
                    self.extra_doubts.append(Doubt("next_visit_date", r.value, "date"))
            elif r and r.kind == "ambiguous":
                self.extra_doubts.append(Doubt("next_visit_date", None, "date"))
        if changed:
            self._emit_record()
        alerts = self._alerts(new)                           # rule alerts first, never deferred
        concern = self._add_concern(text, flag) if flag or is_worry(words) else []
        return alerts + concern + self._take_unspoken()

    def followup(self) -> list[str]:
        """Wait for the LLM's reading of the last sentences; return anything new to speak
        (an alert only the LLM caught, or the out-of-scope line). Call after speaking hear()."""
        self._drain(wait=True)
        return self._take_unspoken()

    def readback(self) -> list[str]:
        self._drain(wait=True)
        out = self._take_unspoken()
        # Only fields with a fixed spoken form are asked aloud (free text from the LLM is never
        # spoken); in discreet mode sensitive fields are skipped. The rest stay on the screen.
        doubts = [d for d in find_doubts(self.record, self.subject, self.today, self.extra_doubts)
                  if d.field in FIELD_NAMES and not (self.discreet and d.field in SENSITIVE_FIELDS)]
        p = plan({}, self.subject, self.today, self.danger.safety_questions(), extras=doubts)
        asked = len(out)
        q = p.question
        if q and q.alternative is not None:
            out.append(self.speaker.choice(q.field, q.value, q.alternative, q.value))
        elif q and q.value is not None:
            out.append(self.speaker.confirm(q.field, q.value))
        if p.safety_signs:
            out.append(self.speaker.safety_turn(p.safety_signs))
        if len(out) == asked:
            out.append(self.speaker.say("summary", summary=self._summary()))
        for line in out[asked:]:
            self._events.append({"type": "question", "text": line})
        return out

    def events(self) -> list[dict]:
        """Browser events since the last call; the queue is cleared."""
        self._drain(wait=False)                 # finished LLM results reach the screen early
        out, self._events = self._events, []
        return out

    # ---------- LLM merge ----------

    def _drain(self, wait: bool) -> None:
        still = []
        for job, text, idx, rule_fields in self._pending:
            if not wait and not job.done():
                still.append((job, text, idx, rule_fields))
                continue
            try:
                result = job.result(timeout=LLM_WAIT_S)
            except Exception as e:              # llm.understand catches its own errors; this is a backstop
                log.warning("llm job failed: %s: %s", type(e).__name__, e)
                continue
            self._merge(result, text, idx, rule_fields)
        self._pending = still

    def _merge(self, result: dict, text: str, idx: int, rule_fields: set[str]) -> None:
        """Rules win for numbers and dates; the LLM only fills what is still empty, except for
        fields she explicitly corrects. Either checker can flag a danger sign."""
        if not result.get("ok"):
            return
        llm_fields, quotes = result.get("fields", {}), result.get("evidence", {})
        patch, words = {}, {}
        for name, value in llm_fields.items():
            if name in LLM_FIELDS:
                patch[LLM_FIELDS[name]], words[LLM_FIELDS[name]] = value, quotes.get(name, text)
        if "bp_systolic" in llm_fields and "bp_diastolic" in llm_fields:
            patch["bp"] = (llm_fields["bp_systolic"], llm_fields["bp_diastolic"])
            words["bp"] = quotes.get("bp_systolic", text)
        if "temperature" in llm_fields:
            t = llm_fields["temperature"]
            patch["temperature"], words["temperature"] = (t["value"], t["unit"]), quotes.get("temperature", text)
        named = {LLM_FIELDS.get(f, f) for f in result.get("correction_of", [])}
        if {"bp_systolic", "bp_diastolic"} & set(result.get("correction_of", [])):
            named.add("bp")
        patch = {k: v for k, v in patch.items() if k not in rule_fields}      # rules win
        fill = {k: v for k, v in patch.items() if k not in self.record}
        fixed = apply_correction(self.record, patch, named).applied
        changed = {**fill, **fixed}
        for k, v in changed.items():
            self._set(k, v, words[k])
        for f in result.get("unsure", []):              # unclear words: doubt the value, whoever set it
            f = "bp" if f in ("bp_systolic", "bp_diastolic") else LLM_FIELDS.get(f, f)
            if f in self.record and not any(d.field == f for d in self.extra_doubts):
                self.extra_doubts.append(Doubt(f, self.record[f], "llm_unsure"))

        new = self.danger.add_vitals({k: v for k, v in changed.items()
                                      if k in ("bp", "temperature", "breaths_per_min", "weight_kg")})
        for s in result.get("danger_signs", []):
            if s["status"] in ("present", "past") and self.danger.add_external(
                    s["id"], s.get("evidence") or text, idx, history=s["status"] == "past"):
                new.append(s["id"])
        if changed:
            self._emit_record()
        self._unspoken += self._alerts(new)
        if result.get("off_topic"):
            self._unspoken.append(self.speaker.say("out_of_scope"))

    def _take_unspoken(self) -> list[str]:
        out, self._unspoken = self._unspoken, []
        return out

    # ---------- internals ----------

    # ---------- worker concerns (outside the checklist; never change a checklist state) ----------

    def _add_concern(self, text: str, flagged: bool) -> list[str]:
        self.record.setdefault("worker_concerns", []).append(
            {"quote": text, "at": now(), "flagged": flagged})      # her words, verbatim
        self._emit_record()
        return [self.speaker.say("concern_flagged" if flagged else "concern_noted")]

    def _flag_last_concern(self) -> str:
        concerns = self.record.get("worker_concerns", [])
        if not concerns:
            return self.speaker.say("concern_missing")
        target = next((c for c in reversed(concerns) if not c["flagged"]), concerns[-1])
        target["flagged"] = True
        self._emit_record()
        return self.speaker.say("concern_flagged")

    def _set(self, key: str, value, words: str) -> None:
        if key in self.record and self.record[key] != value:     # a new reading replaces old doubts
            self.extra_doubts = [d for d in self.extra_doubts if d.field != key]
        self.record[key] = value
        self.evidence[key] = words

    def _alerts(self, signs: list[str]) -> list[str]:
        """Speak and show each newly present sign once. Escalation is never deferred."""
        out = []
        for s in signs:
            if s in self.alerted:
                continue
            self.alerted.append(s)
            out.append(self.speaker.alert(s))
            event = self._alert_event(s)
            self._events.append(event)
            last = self.danger.states[s].evidence[-1]
            self.flags.append({"sign": s, "quote": event["quote"], "at": now(),
                               "by": "llm" if last.phrase == "llm" else "rules"})
        return out

    def _alert_event(self, sign: str) -> dict:
        meta = self.danger.lex.signs[sign]
        quote = next((e.quote for e in reversed(self.danger.states[sign].evidence)
                      if e.status == "present"), "")
        return {"type": "alert", "sign": sign, "label": sign_label(sign),
                "local": spoken_sign(sign, self.lang), "quote": quote,
                "source": meta.get("source"), "page": meta.get("page")}

    def _emit_record(self) -> None:
        self._events.append({"type": "record", "fields": jsonable(self.record),
                             "evidence": dict(self.evidence)})

    def _save(self) -> list[str]:
        rows = [{**r, "label": sign_label(r["sign"]), "local": spoken_sign(r["sign"], self.lang)}
                for r in self.danger.receipt()]
        if self.store:
            try:
                self.visit_id = self.store.save_visit(
                    beneficiary_id=self.beneficiary_id, visit_type=self.visit_type, lang=self.lang,
                    saved_at=now(), record=jsonable(self.record), transcript=self.transcript,
                    receipt=rows, flags=self.flags, concerns=self.record.get("worker_concerns", []))
            except Exception:                   # never claim "saved" when the disk write failed
                log.exception("saving the visit failed")
                return [self.speaker.say("save_failed")]
        self.saved, self.saved_at = True, self.clock()
        self._emit_record()
        self._events.append({"type": "receipt", "rows": rows})
        self._events.append({"type": "saved"})
        return [self.speaker.say("saved")]

    def _summary(self) -> str:
        spoken = ("weight_kg", "bp", "hb", "next_visit_date")     # never a SENSITIVE_FIELDS entry
        parts = [self.speaker.confirm(f, v).rsplit(",", 1)[0]
                 for f, v in self.record.items() if f in spoken]
        return "; ".join(parts) or "Koi naya maap nahi"
