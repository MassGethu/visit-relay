"""Medicines already given (by another ASHA, the ANM or the PHC): recorded, never spoken."""
import datetime as dt

import pytest

from asha.guard import guard
from asha.medicines import merge, read
from asha.visit import Visit

TODAY = dt.date(2026, 11, 21)


def make(visit_type: str = "anc", subject: str = "mother") -> Visit:
    v = Visit(visit_type, subject, "hi", today=TODAY, use_llm=False, use_store=False)
    v.start()
    return v


def names(text: str) -> list[str]:
    return [m["name"] for m in read(text)[0]]


@pytest.mark.parametrize("text", [
    "IFA goli di", "i f a tablets given", "आईएफए की गोली दी", "आयरन की गोली दी थी",
    "lohe ki goli le rahi hai", "khoon ki goli di", "ಕಬ್ಬಿಣದ ಮಾತ್ರೆ ಕೊಟ್ಟಿದ್ದಾರೆ", "folic acid diya",
])
def test_ifa_is_recognised_in_hindi_kannada_and_english(text):
    assert names(text) == ["IFA tablets"]


@pytest.mark.parametrize("text, expected", [
    ("calcium ki goli di", "Calcium tablets"), ("ಕ್ಯಾಲ್ಸಿಯಂ ಮಾತ್ರೆ ಕೊಟ್ಟಿದ್ದಾರೆ", "Calcium tablets"),
    ("pet ke keede ki goli di", "Deworming (albendazole)"), ("albendajol di", "Deworming (albendazole)"),
    ("ORS ke packet diye", "ORS"), ("जीवन रक्षक घोल दिया", "ORS"), ("zinc goli di", "Zinc tablets"),
    ("vitamin a pilaya", "Vitamin A"),
])
def test_other_kit_medicines_are_recognised(text, expected):
    assert names(text) == [expected]


def test_count_and_another_asha_are_captured():
    found, denied = read("pichli ASHA ne tees IFA goli di thi, calcium bhi")
    assert found == [{"name": "IFA tablets", "count": 30, "by": "another ASHA"},
                     {"name": "Calcium tablets", "count": None, "by": "another ASHA"}]
    assert denied == set()


@pytest.mark.parametrize("text, by", [
    ("दूसरी आशा ने 30 आयरन की गोली दी थी", "another ASHA"), ("ಬೇರೆ ಆಶಾ ಐಎಫ್ಎ ಕೊಟ್ಟಿದ್ದಾರೆ", "another ASHA"),
    ("ANM ne vitamin a pilaya", "ANM"), ("hospital mein calcium mila", "PHC / hospital"),
    ("IFA goli di", None),
])
def test_who_gave_it(text, by):
    assert read(text)[0][0]["by"] == by


def test_days_are_not_a_tablet_count():
    assert read("30 din ki IFA goli di")[0][0]["count"] is None


def test_negation_only_denies_its_own_clause():
    found, denied = read("IFA di aur calcium nahi diya")
    assert [m["name"] for m in found] == ["IFA tablets"]
    assert denied == {"Calcium tablets"}


@pytest.mark.parametrize("text", ["ಕ್ಯಾಲ್ಸಿಯಂ ಮಾತ್ರೆ ಕೊಟ್ಟಿಲ್ಲ", "calcium nahi diya", "calcium band kar diya"])
def test_negated_mentions_are_denied(text):
    assert read(text) == ([], {"Calcium tablets"})


@pytest.mark.parametrize("text", ["IFA goli kitni dein", "kya calcium dena hai?", "wajan baavan kilo", "sab theek hai"])
def test_questions_and_unrelated_notes_record_nothing(text):
    assert read(text) == ([], set())


def test_merge_keeps_known_details_and_removes_denied():
    current = [{"name": "IFA tablets", "count": 30, "by": "another ASHA"},
               {"name": "Calcium tablets", "count": None, "by": None}]
    updated = merge(current, [{"name": "IFA tablets", "count": None, "by": None}], {"Calcium tablets"})
    assert updated == [{"name": "IFA tablets", "count": 30, "by": "another ASHA"}]


# ---------- in a visit ----------

def test_visit_records_medicines_instantly_with_her_words():
    v = make()
    text = "pichli ASHA ne tees IFA goli di thi"
    v.hear(text)
    assert v.record["medicines_given"] == [{"name": "IFA tablets", "count": 30, "by": "another ASHA"}]
    assert v.evidence["medicines_given"] == text
    record_events = [e for e in v.events() if e["type"] == "record"]
    assert record_events[-1]["fields"]["medicines_given"][0]["name"] == "IFA tablets"


def test_a_later_no_removes_the_medicine():
    v = make()
    v.hear("calcium ki goli di")
    v.hear("nahi, calcium nahi diya")
    assert "medicines_given" not in v.record


def test_medicine_names_are_never_spoken():
    v = make()
    lines = v.hear("pichli ASHA ne IFA aur calcium ki goli di")
    lines += v.readback()
    assert not any(w in line.lower() for line in lines for w in ("ifa", "calcium", "goli"))
    assert all(guard(line, "hi")[1] == [] for line in lines)


def test_medicine_question_is_not_recorded():
    v = make()
    v.hear("kaunsi dawai dein, IFA ya calcium?")
    assert "medicines_given" not in v.record
