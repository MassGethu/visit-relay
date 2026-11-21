"""Visit flow: browser events, LLM merge, corrections, undo, discreet mode (no network)."""
import datetime as dt
import json

import pytest

from asha.visit import Visit

TODAY = dt.date(2026, 11, 13)


def make(visit_type="anc", subject="mother", **kw) -> Visit:
    kw.setdefault("use_llm", False)
    v = Visit(visit_type, subject=subject, lang="hi", today=TODAY, **kw)
    v.start()
    return v


def types(events):
    return [e["type"] for e in events]


# ---------- events() ----------

def test_events_are_returned_once_then_cleared():
    v = make()
    v.hear("wajan baavan kilo")
    first = v.events()
    assert types(first) == ["record"]
    assert first[0]["fields"] == {"weight_kg": 52.0}
    assert first[0]["evidence"] == {"weight_kg": "wajan baavan kilo"}
    assert v.events() == []


def test_danger_sign_gives_an_alert_event_with_source():
    v = make()
    lines = v.hear("thoda khoon aa raha tha kal, ab nahi")
    alert = [e for e in v.events() if e["type"] == "alert"]
    assert len(lines) == 1 and "PHC" in lines[0]
    assert alert[0]["sign"] == "anc_vaginal_bleeding"
    assert alert[0]["label"] and alert[0]["local"] and alert[0]["quote"]
    assert alert[0]["source"] and alert[0]["page"]


def test_same_sign_alerts_only_once():
    v = make()
    v.hear("khoon aa raha hai")
    v.events()
    assert v.hear("abhi bhi khoon aa raha hai") == []
    assert "alert" not in types(v.events())


def test_readback_lines_become_question_events():
    v = make(subject="newborn", visit_type="hbnc")
    v.hear("wajan athais kilo")
    v.events()
    lines = v.readback()
    assert [e["text"] for e in v.events()] == lines


def test_save_sends_record_receipt_saved_and_all_events_are_json():
    v = make()
    v.hear("BP ek sau bees by assi, agla visit 20 november ko aana hai")
    v.hear("record pakka")
    ev = v.events()
    assert types(ev)[-3:] == ["record", "receipt", "saved"]
    rows = ev[-2]["rows"]
    assert {r["status"] for r in rows} <= {"present", "ruled_out", "not_checked"}
    assert all(r["label"] for r in rows)
    json.dumps(ev)                              # dates and tuples are serialisable
    assert ev[-3]["fields"]["bp"] == [120, 80]
    assert ev[-3]["fields"]["next_visit_date"] == "2026-11-20"


# ---------- LLM alongside the rules ----------

def llm_says(**result):
    """A fake llm.understand that returns a fixed answer."""
    base = {"ok": True, "fields": {}, "evidence": {}, "unsure": [], "correction_of": [],
            "danger_signs": [], "off_topic": False}
    return lambda text, visit_type, record: {**base, **result}


def test_rule_alert_does_not_wait_for_a_slow_llm():
    import threading
    gate = threading.Event()

    def slow(text, visit_type, record):
        gate.wait(5)
        return {"ok": False, "error": "slow"}

    v = make(use_llm=True, understand=slow)
    lines = v.hear("thoda khoon aa raha hai")      # returns while the LLM is still blocked
    assert len(lines) == 1 and "PHC" in lines[0]
    gate.set()
    assert v.followup() == []


def test_llm_only_danger_sign_is_spoken_by_followup():
    v = make("hbnc", "newborn", use_llm=True, understand=llm_says(
        danger_signs=[{"id": "nb_poor_feeding", "status": "present", "evidence": "doodh nahi pee raha"}]))
    v.hear("doodh nahi pee raha")
    lines = v.followup()
    assert len(lines) == 1 and "PHC" in lines[0]
    assert v.danger.states["nb_poor_feeding"].status == "present"
    assert any(e["type"] == "alert" and e["sign"] == "nb_poor_feeding" for e in v.events())


def test_llm_absent_never_rules_out_a_sign():
    v = make(use_llm=True, understand=llm_says(
        danger_signs=[{"id": "anc_convulsions", "status": "absent", "evidence": "fits nahi"}]))
    v.hear("kuch nahi")
    v.followup()
    assert v.danger.states["anc_convulsions"].status == "not_checked"


def test_llm_past_sign_is_present_with_history():
    v = make(use_llm=True, understand=llm_says(
        danger_signs=[{"id": "anc_convulsions", "status": "past", "evidence": "pehle jhatke aaye"}]))
    v.hear("pehle jhatke aaye the")
    v.followup()
    st = v.danger.states["anc_convulsions"]
    assert st.status == "present" and st.evidence[-1].history


def test_rules_win_for_numbers_and_llm_fills_the_rest():
    v = make(use_llm=True, understand=llm_says(
        fields={"weight_kg": 3.8, "ifa_taking": True, "bp_systolic": 120, "bp_diastolic": 80},
        evidence={"ifa_taking": "IFA goli roz le rahi hai"}))
    v.hear("wajan baavan kilo, BP ek sau bees by assi, IFA goli roz le rahi hai")
    v.followup()
    assert v.record["weight_kg"] == 52.0             # rules, not the LLM's 3.8
    assert v.record["bp"] == (120, 80)
    assert v.record["ifa_taking"] is True
    assert v.evidence["ifa_taking"] == "IFA goli roz le rahi hai"


def test_llm_never_overwrites_an_earlier_value_without_a_correction():
    answers = iter([llm_says()(None, None, None),
                    llm_says(fields={"hb": 11.0})(None, None, None)])
    v = make(use_llm=True, understand=lambda *a: next(answers))
    v.hear("hb saadhe nau")
    v.followup()
    v.hear("aur kuch baat")
    v.followup()
    assert v.record["hb"] == 9.5


def test_llm_vitals_raise_danger_signs():
    v = make(use_llm=True, understand=llm_says(fields={"bp_systolic": 160, "bp_diastolic": 110}))
    v.hear("pressure bahut zyada tha")
    lines = v.followup()
    assert lines and "PHC" in lines[0]


def test_llm_unsure_field_becomes_a_readback_question():
    v = make(use_llm=True, understand=llm_says(fields={"hb": 9.0}, unsure=["hb"]))
    v.hear("hb shayad nau")
    lines = v.readback()                             # readback waits for the LLM itself
    assert any("HB" in line for line in lines)


def test_off_topic_gets_the_fixed_out_of_scope_line():
    v = make(use_llm=True, understand=llm_says(off_topic=True))
    v.hear("isko kaunsi dawai dein")
    assert v.followup() == ["Main sirf visit record mein madad kar sakti hoon."]


def test_llm_failure_leaves_the_rules_result():
    v = make(use_llm=True, understand=lambda *a: {"ok": False, "error": "down"})
    v.hear("wajan baavan kilo")
    assert v.followup() == [] and v.record == {"weight_kg": 52.0}


def test_save_waits_for_pending_llm_so_nothing_is_lost():
    v = make("hbnc", "newborn", use_llm=True, understand=llm_says(
        danger_signs=[{"id": "nb_poor_feeding", "status": "present", "evidence": "doodh nahi"}]))
    v.hear("doodh nahi pee raha")
    lines = v.hear("record pakka")                   # no followup() call in between
    assert "PHC" in lines[0] and "save" in lines[-1]
    receipt = next(e for e in v.events() if e["type"] == "receipt")
    assert any(r["sign"] == "nb_poor_feeding" and r["status"] == "present" for r in receipt["rows"])


# ---------- corrections and undo ----------

class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_self_correction_keeps_the_last_number_and_her_words():
    v = make("hbnc", "newborn")
    v.hear("wajan 2.6 nahi 2.8 kilo")
    assert v.record == {"weight_kg": 2.8}
    assert v.evidence["weight_kg"] == "wajan 2.6 nahi 2.8 kilo"


def test_correction_changes_only_the_named_field():
    v = make()
    v.hear("wajan baavan kilo, hb saadhe nau")
    v.hear("nahi, hb das hai")
    assert v.record == {"weight_kg": 52.0, "hb": 10.0}


def test_answering_the_choice_question_clears_that_doubt():
    v = make("hbnc", "newborn")
    v.hear("wajan athais kilo")
    assert "ya" in v.readback()[0]                   # "28 ya 2.8?"
    v.hear("do point aath")
    v.hear("wajan do point aath kilo")
    lines = v.readback()
    assert not any("Wajan" in line and " ya " in line for line in lines)


def test_llm_correction_overwrites_only_the_named_field():
    answers = iter([
        llm_says(fields={"ifa_taking": True, "vaccines_given": ["BCG"]})(None, None, None),
        llm_says(fields={"ifa_taking": False, "vaccines_given": ["OPV"]},
                 correction_of=["ifa_taking"])(None, None, None),
    ])
    v = make(use_llm=True, understand=lambda *a: next(answers))
    v.hear("IFA le rahi hai, BCG lag gaya")
    v.followup()
    v.hear("nahi, IFA nahi le rahi")
    v.followup()
    assert v.record["ifa_taking"] is False
    assert v.record["vaccinations_given"] == ["BCG"]    # not named: unchanged


def test_a_later_no_never_clears_a_danger_sign():
    v = make()
    v.hear("khoon aa raha hai")
    v.hear("nahi nahi, khoon nahi aa raha")
    st = v.danger.states["anc_vaginal_bleeding"]
    assert st.status == "present" and st.disputed


def test_bare_haan_never_saves():
    v = make()
    v.hear("haan")
    assert not v.saved


def test_ruko_within_five_seconds_undoes_the_save():
    clock = FakeClock()
    v = make(clock=clock)
    v.hear("record pakka")
    clock.now += 3
    lines = v.hear("ruko")
    assert not v.saved and "radd" in lines[0]
    assert v.events()[-1] == {"type": "undo"}
    v.hear("wajan baavan kilo")                      # she can change things again
    assert v.record["weight_kg"] == 52.0


def test_ruko_after_five_seconds_does_nothing():
    clock = FakeClock()
    v = make(clock=clock)
    v.hear("record pakka")
    clock.now += 6
    assert v.hear("ruko") == [] and v.saved


# ---------- discreet mode ----------

def test_dheere_turns_on_discreet_mode():
    v = make()
    lines = v.hear("dheere")
    assert v.discreet and "niji" in lines[0]
    assert {"type": "discreet", "on": True} in v.events()


def test_dheere_inside_a_long_sentence_is_content_not_a_command():
    v = make("hbnc", "newborn")
    v.hear("baby bahut dheere dheere saans le raha hai")
    assert not v.discreet


def test_danger_signs_are_still_spoken_in_discreet_mode():
    v = make()
    v.hear("dheere")
    lines = v.hear("thoda khoon aa raha hai")
    assert len(lines) == 1 and "PHC" in lines[0]


def test_sensitive_question_is_not_read_aloud_in_discreet_mode():
    from asha.readback import Doubt
    v = make()
    v.hear("dheere")
    v.record["family_planning"] = "copper-t"
    v.extra_doubts.append(Doubt("family_planning", "copper-t", "llm_unsure"))
    assert not any("copper" in line.lower() for line in v.readback())


def test_every_template_line_still_passes_the_guard():
    from asha.guard import guard
    from asha.speak import TEMPLATES
    for key in ("discreet_on", "undone"):
        for lang, text in TEMPLATES[key].items():
            assert guard(text, lang)[1] == [], (key, lang)


@pytest.mark.parametrize("field, value", [
    ("ifa_taking", True), ("vaccinations_given", ["BCG"]), ("next_visit_text", "agle hafte")])
def test_doubt_on_a_free_text_field_is_not_spoken_and_does_not_crash(field, value):
    from asha.readback import Doubt
    v = make()
    v.record[field] = value
    v.extra_doubts.append(Doubt(field, value, "llm_unsure"))
    lines = v.readback()
    assert not any(str(value) in line for line in lines)
