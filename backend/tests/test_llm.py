"""LLM layer: prompt building, schema validation and Groq -> Ollama fallback (no network)."""
import json

import pytest

import llm


def ok_json(**extra) -> str:
    return json.dumps({"fields": {}, "danger_signs": [], **extra})


# ---------- prompt ----------

def test_prompt_lists_only_signs_for_the_visit_type():
    p = llm.system_prompt("anc")
    assert "{DANGER_SIGN_LIST}" not in p
    assert "anc_vaginal_bleeding: Bleeding from vagina" in p
    assert "nb_poor_feeding" not in p


def test_hbnc_prompt_covers_mother_and_newborn():
    ids = llm.allowed_sign_ids("hbnc")
    assert "nb_poor_feeding" in ids and "pnc_heavy_bleeding" in ids
    assert "anc_vaginal_bleeding" not in ids


def test_user_message_carries_record_and_sentence():
    m = llm.user_message("wajan 52 kilo", "anc", {"hb": 9.5})
    assert "VISIT_TYPE: anc" in m and '"hb": 9.5' in m and m.endswith("SENTENCE: wajan 52 kilo")


# ---------- validation ----------

def test_validate_keeps_good_fields_and_drops_bad_ones():
    raw = {"fields": {"weight_kg": "2.8", "hb": True, "bp_systolic": 120, "subject": "father",
                      "temperature": {"value": 101, "unit": "f"}, "ifa_taking": "yes",
                      "vaccines_given": ["BCG", "", 3], "made_up": 1},
           "evidence": {"weight_kg": "do kilo aath sau", "hb": "x", "bp_systolic": 120}}
    out = llm.validate(raw, "anc")
    assert out["fields"] == {"weight_kg": 2.8, "bp_systolic": 120,
                             "temperature": {"value": 101, "unit": "F"}, "vaccines_given": ["BCG"]}
    assert out["evidence"] == {"weight_kg": "do kilo aath sau"}


def test_validate_rejects_negative_and_zero_numbers():
    out = llm.validate({"fields": {"weight_kg": -3, "hb": 0}}, "anc")
    assert out["fields"] == {}


def test_validate_drops_sign_ids_outside_the_visit_and_bad_statuses():
    raw = {"danger_signs": [{"id": "nb_poor_feeding", "status": "present", "evidence": "x"},
                            {"id": "anc_vaginal_bleeding", "status": "maybe"},
                            {"id": "anc_convulsions", "status": "past", "evidence": "pehle jhatke"},
                            "garbage"]}
    out = llm.validate(raw, "anc")
    assert out["danger_signs"] == [{"id": "anc_convulsions", "status": "past", "evidence": "pehle jhatke"}]


def test_duplicate_sign_present_beats_absent():
    raw = {"danger_signs": [{"id": "anc_vaginal_bleeding", "status": "absent", "evidence": "nahi"},
                            {"id": "anc_vaginal_bleeding", "status": "present", "evidence": "khoon"},
                            {"id": "anc_vaginal_bleeding", "status": "absent", "evidence": "ab nahi"}]}
    out = llm.validate(raw, "anc")
    assert out["danger_signs"] == [{"id": "anc_vaginal_bleeding", "status": "present", "evidence": "khoon"}]


def test_validate_filters_unsure_correction_and_off_topic():
    out = llm.validate({"unsure": ["weight_kg", "nonsense", 4], "correction_of": ["hb"],
                        "off_topic": "true"}, "pnc")
    assert out["unsure"] == ["weight_kg"] and out["correction_of"] == ["hb"]
    assert out["off_topic"] is False      # only a real JSON true counts


def test_validate_survives_wrong_top_level_types():
    out = llm.validate({"fields": [1, 2], "evidence": "x", "danger_signs": None}, "anc")
    assert out["fields"] == {} and out["evidence"] == {} and out["danger_signs"] == []


def test_parse_json_strips_code_fences_and_rejects_non_objects():
    assert llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        llm.parse_json("[1, 2]")


# ---------- provider fallback ----------

def boom(*_):
    raise RuntimeError("down")


def test_groq_answer_is_used_first(monkeypatch):
    monkeypatch.setattr(llm, "call_groq", lambda s, u: ok_json(fields={"hb": 9.5}))
    monkeypatch.setattr(llm, "call_ollama", lambda s, u: pytest.fail("ollama should not be called"))
    out = llm.understand("hb saadhe nau", "anc", {})
    assert out["ok"] and out["provider"] == "groq" and out["fields"] == {"hb": 9.5}


def test_falls_back_to_ollama_when_groq_fails(monkeypatch):
    monkeypatch.setattr(llm, "call_groq", boom)
    monkeypatch.setattr(llm, "call_ollama", lambda s, u: ok_json(fields={"weight_kg": 52}))
    out = llm.understand("wajan baavan kilo", "anc", {})
    assert out["ok"] and out["provider"] == "ollama" and out["fields"] == {"weight_kg": 52}


def test_falls_back_when_groq_returns_broken_json(monkeypatch):
    monkeypatch.setattr(llm, "call_groq", lambda s, u: "not json")
    monkeypatch.setattr(llm, "call_ollama", lambda s, u: ok_json())
    assert llm.understand("x", "anc", {})["provider"] == "ollama"


def test_both_fail_returns_not_ok_with_reasons(monkeypatch):
    monkeypatch.setattr(llm, "call_groq", boom)
    monkeypatch.setattr(llm, "call_ollama", boom)
    out = llm.understand("x", "anc", {})
    assert out == {"ok": False, "error": "groq: RuntimeError: down; ollama: RuntimeError: down"}


def test_missing_keys_fail_fast_without_network(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.call_groq("s", "u")
    with pytest.raises(RuntimeError, match="LOCAL_MODEL"):
        llm.call_ollama("s", "u")
