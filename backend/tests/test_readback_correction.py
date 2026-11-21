import datetime as dt

from asha.correction import apply_correction, is_commit, is_undo
from asha.readback import after_safety_turn, decimal_shift_alternative, find_doubts, plan

TODAY = dt.date(2026, 11, 13)


def test_clean_visit_has_no_question():
    p = plan({"weight_kg": 2.8, "next_visit_date": dt.date(2026, 11, 20)}, "newborn", TODAY, [])
    assert p.question is None and p.safety_signs == []


def test_implausible_weight_becomes_a_choice():
    p = plan({"weight_kg": 28.0}, "newborn", TODAY, [])
    assert p.question.kind == "out_of_range" and p.question.alternative == 2.8


def test_only_one_non_safety_question_highest_priority_first():
    rec = {"weight_kg": 28.0, "next_visit_date": dt.date(2026, 10, 1), "_unsure": ["hb"], "hb": 9.0}
    assert len(find_doubts(rec, "newborn", TODAY)) == 3
    assert plan(rec, "newborn", TODAY, []).question.field == "weight_kg"


def test_contradiction_newborn_with_tt():
    d = find_doubts({"vaccinations_due": ["TT-2"]}, "newborn", TODAY)
    assert d[0].kind == "contradiction"


def test_safety_turn_capped_and_unanswered_left_for_anm():
    p = plan({}, "mother", TODAY, ["a", "b", "c", "d"])
    assert p.safety_signs == ["a", "b", "c"]
    assert after_safety_turn(p.safety_signs, {"a"}) == ["b", "c"]


def test_decimal_shift():
    assert decimal_shift_alternative(520, "weight_mother") == 52.0
    assert decimal_shift_alternative(5.2, "weight_mother") == 52.0


def test_correction_changes_only_named_fields():
    r = apply_correction({"weight_kg": 2.6, "hb": 9.5}, {"weight_kg": 2.8, "hb": 11}, {"weight_kg"})
    assert r.record == {"weight_kg": 2.8, "hb": 9.5} and r.rejected == {"hb": 11}


def test_correction_cannot_clear_a_danger_sign():
    r = apply_correction({}, {"clear_signs": ["anc_vaginal_bleeding"]}, set(), {"anc_vaginal_bleeding"})
    assert r.disputed_signs == ["anc_vaginal_bleeding"]


def test_commit_needs_the_phrase_not_just_haan():
    assert is_commit("haan record pakka")
    assert not is_commit("haan")
    assert is_undo("ruko", 3.0) and not is_undo("ruko", 6.0)
