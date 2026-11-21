"""Out-of-scope replies, "which visit is this?" questions and switching the visit type."""
import datetime as dt

import pytest

from asha.concern import words_of
from asha.context import answer_to_switch, context_cues, out_of_scope
from asha.guard import guard
from asha.visit import Visit

TODAY = dt.date(2026, 11, 21)
SUBJECT = {"anc": "mother", "pnc": "mother", "hbnc": "newborn", "hbyc": "child"}
OUT_OF_SCOPE = "Main sirf visit record mein madad kar sakti hoon."
RESUME = "Chaliye, visit aage badhaate hain."


def make(visit_type: str, **kw) -> Visit:
    v = Visit(visit_type, SUBJECT[visit_type], "hi", today=TODAY, use_llm=False, use_store=False, **kw)
    v.start()
    return v


def llm_says(**result):
    base = {"ok": True, "fields": {}, "evidence": {}, "unsure": [], "correction_of": [],
            "danger_signs": [], "off_topic": False, "visit_context": None}
    return lambda text, visit_type, record: {**base, **result}


# ---------- out of scope ----------

@pytest.mark.parametrize("text", ["kaunsi dawai dein?", "bukhaar ki dawa batao", "कौन सी दवा दें",
                                  "kya bimari hai", "which medicine should she take"])
def test_medicine_or_diagnosis_question_is_out_of_scope(text):
    assert out_of_scope(words_of(text))


@pytest.mark.parametrize("text", ["IFA ki goli le rahi hai", "dawai le rahi hai", "wajan baavan kilo"])
def test_ordinary_visit_talk_is_not_out_of_scope(text):
    assert not out_of_scope(words_of(text))


@pytest.mark.parametrize("visit_type", ["anc", "pnc", "hbnc", "hbyc"])
def test_every_visit_type_answers_out_of_scope_then_resumes(visit_type):
    v = make(visit_type)
    assert v.hear("kaunsi dawai dein?") == [OUT_OF_SCOPE, RESUME]


def test_after_the_readback_out_of_scope_resumes_with_the_next_checklist_questions():
    v = make("anc")
    v.readback()
    lines = v.hear("kaunsi dawai dein?")
    assert lines[0] == OUT_OF_SCOPE and lines[1].startswith("<pauses> Ek-ek karke bataiye")


def test_a_danger_sign_in_a_medicine_question_still_alerts_first():
    lines = make("hbyc").hear("do hafte se dast hai, kaunsi dawai dein?")
    assert "PHC" in lines[0] and lines[1:] == [OUT_OF_SCOPE, RESUME]


# ---------- context cues ----------

@pytest.mark.parametrize("visit_type, text, want", [
    ("anc", "baby ko bukhaar hai", {"hbnc", "hbyc"}),
    ("anc", "teen saal ka bachcha hai", {"hbyc"}),
    ("pnc", "baby ko doodh nahi pee raha", {"hbnc"}),
    ("hbnc", "pet mein bachcha hil nahi raha", {"anc"}),
    ("hbyc", "pet mein bachcha hil nahi raha", {"anc"}),
])
def test_a_sentence_about_another_visit_is_noticed(visit_type, text, want):
    assert context_cues(words_of(text), text, visit_type, matched_here=False) == want


@pytest.mark.parametrize("visit_type, text", [
    ("anc", "bachcha kam hil raha hai"),           # the baby in the womb: still pregnancy
    ("hbnc", "maa ko bukhaar hai"),                # HBNC covers the mother after delivery
    ("hbyc", "teen saal ka bachcha, bukhaar nahi hai"),
    ("pnc", "wajan baavan kilo"),
])
def test_a_sentence_about_this_visit_raises_no_question(visit_type, text):
    assert context_cues(words_of(text), text, visit_type, matched_here=False) == set()


@pytest.mark.parametrize("text, want", [
    ("haan", "yes"), ("haan ji badlo", "yes"), ("ಹೌದು", "yes"), ("nahi", "no"), ("mat karo", "no"),
    ("navjaat", "hbnc"), ("newborn visit", "hbnc"), ("garbhavastha", "anc"),
    ("bukhaar nahi hai", None), ("nahi navjaat", None), ("teen saal ka bachcha hai aur bukhaar hai", None),
])
def test_her_answer_to_switch_the_visit(text, want):
    assert answer_to_switch(words_of(text)) == want


# ---------- asking and switching ----------

def test_one_other_visit_asks_yes_or_no_and_yes_switches():
    v = make("hbnc")
    assert v.hear("pet mein bachcha hil nahi raha") == [
        "Yeh garbhavastha ki baat lagti hai. Visit badal doon? Haan ya nahi."]
    assert {"type": "visit_context", "current": "hbnc", "suggested": ["anc"]} in v.events()
    lines = v.hear("haan")
    assert lines[0] == "Theek hai, ab garbhavastha visit." and "PHC" in lines[1]
    assert (v.visit_type, v.subject) == ("anc", "mother")
    assert "anc_reduced_fetal_movement" in v.danger.present()
    assert {"type": "visit_type", "visit_type": "anc", "subject": "mother"} in v.events()


def test_several_other_visits_ask_which_and_a_name_switches():
    v = make("anc")
    lines = v.hear("baby ko bukhaar hai")
    assert lines[-1] == "Yeh kis visit ki baat hai: garbhavastha, navjaat shishu ya chhote bachche?"
    assert v.hear("haan") == [lines[-1]]           # "yes" does not say which: ask again
    v.hear("navjaat")
    assert v.visit_type == "hbnc" and "nb_fever" in v.danger.present()


def test_no_keeps_the_visit_and_the_question_is_never_asked_again():
    v = make("pnc")
    v.hear("baby ko doodh nahi pee raha")
    assert v.hear("nahi") == ["Theek hai, prasav ke baad maa visit hi chalega.", RESUME]
    assert v.visit_type == "pnc"
    assert v.hear("baby ko doodh nahi pee raha") == []


def test_content_after_the_question_drops_it_and_is_heard_as_usual():
    v = make("pnc")
    v.hear("baby ko doodh nahi pee raha")
    v.hear("bahut khoon aa raha hai")
    assert v.visit_type == "pnc" and "pnc_heavy_bleeding" in v.danger.present()
    v.hear("haan")
    assert v.visit_type == "pnc"


def test_switching_never_loses_a_flag_already_raised():
    v = make("anc")
    v.hear("baby ko bukhaar hai")                  # anc_high_fever alerted before the question
    v.set_visit_type("hbnc")
    kept = v.record["flags_before_switch"]
    assert [k["sign"] for k in kept] == ["anc_high_fever"] and kept[0]["quote"]
    assert any(f["sign"] == "anc_high_fever" for f in v.flags)      # still in the audit trail


def test_switching_back_puts_the_sign_on_its_own_checklist_again():
    v = make("hbyc")
    v.hear("do hafte se dast")
    v.set_visit_type("anc")
    v.set_visit_type("hbyc")
    assert "ch_persistent_diarrhoea" in v.danger.present()
    assert "flags_before_switch" not in v.record


def test_a_switch_rechecks_vitals_for_the_new_visit():
    v = make("pnc")
    v.hear("bukhaar sau do degree hai")
    v.set_visit_type("hbnc")
    assert v.danger.present()                      # the temperature is judged on the new checklist


def test_the_screen_dropdown_switch_is_audited_and_saved():
    class FakeStore:
        def save_visit(self, **kw):
            self.kw = kw
            return 1
    store = FakeStore()
    v = Visit("anc", "mother", "hi", today=TODAY, use_llm=False, store=store)
    v.start()
    v.set_visit_type("hbyc")
    v.hear("record pakka")
    assert store.kw["visit_type"] == "hbyc"
    assert [(s["from"], s["to"], s["by"]) for s in store.kw["switches"]] == [("anc", "hbyc", "screen")]


def test_same_visit_or_unknown_type():
    v = make("anc")
    assert v.set_visit_type("anc") == ["Theek hai, garbhavastha visit hi chalega."]
    with pytest.raises(ValueError):
        v.set_visit_type("xyz")


def test_llm_visit_context_asks_when_the_rules_did_not():
    v = make("anc", **{})
    v.use_llm, v.understand = True, llm_says(visit_context="hbyc")
    assert v.hear("woh school nahi jaata") == []
    assert v.followup() == ["Yeh chhote bachche ki baat lagti hai. Visit badal doon? Haan ya nahi."]


def test_llm_never_asks_twice_about_a_sentence_the_rules_answered():
    v = make("anc")
    v.use_llm, v.understand = True, llm_says(visit_context="hbnc", off_topic=True)
    v.hear("baby ko bukhaar hai")
    assert v.followup() == []


@pytest.mark.parametrize("lang", ["hi", "kn", "en"])
def test_every_new_line_passes_the_guard(lang):
    v = Visit("anc", "mother", lang, today=TODAY, use_llm=False, use_store=False)
    v.start()
    lines = [v.speaker.context_question(["hbnc"], "anc"), v.speaker.context_question(["hbnc", "hbyc"], "anc"),
             v.speaker.say("resume"),
             *[v.speaker.say(k, visit=v.speaker.visit_name(t))
               for k in ("visit_switched", "visit_kept") for t in ("anc", "pnc", "hbnc", "hbyc")]]
    for line in lines:
        assert guard(line, lang) == (line, [])
