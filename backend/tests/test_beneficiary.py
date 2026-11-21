import json

import pytest

from asha.beneficiary import SURE, find, load_people
from asha.speak import Speaker

PEOPLE = load_people()


def test_beneficiaries_are_15_synthetic_with_unique_4_digit_ids():
    assert len(PEOPLE) == 15
    assert all(p["synthetic"] is True for p in PEOPLE)
    ids = [p["id"] for p in PEOPLE]
    assert len(set(ids)) == 15 and all(i.isdigit() and len(i) == 4 for i in ids)
    assert {p["visit_type"] for p in PEOPLE} == {"anc", "pnc", "hbnc", "hbyc"}


@pytest.mark.parametrize("said, want_id", [
    ("ID chaar ek do saat", "4127"),
    ("चार एक दो सात", "4127"),
    ("kavya ka baby", "7409"),
    ("sunita devi ka visit", "4381"),
])
def test_clear_id_or_name_is_sure(said, want_id):
    m = find(said, PEOPLE)
    assert m.person["id"] == want_id and m.sure


@pytest.mark.parametrize("said, want_id", [
    ("id 4128", "4127"),            # one digit off
    ("shilpa naayak", "5096"),      # misspelt surname
    ("kavya", "4127"),              # mother and baby both fit: must ask
])
def test_doubtful_match_asks_to_confirm(said, want_id):
    m = find(said, PEOPLE)
    assert m.person["id"] == want_id and m.score < SURE and not m.sure


@pytest.mark.parametrize("said", ["theek hai", "", "id"])
def test_no_name_or_id_gives_no_match(said):
    assert find(said, PEOPLE) is None


def test_confirm_question_names_person_and_speaks_id_digits():
    sp = Speaker("hi")
    sp.say("disclosure")
    line = sp.confirm_beneficiary({"id": "4127", "name": "Kavya Gowda"})
    assert line.startswith("Kya aap Kavya Gowda, ID ") and "4127" not in line


@pytest.mark.parametrize("said, want_id", [
    ("काव्या का बच्चा", "7409"),       # Prisma writes Hindi in Devanagari
    ("काव्या गौड़ा", "4127"),           # whole name of the mother, not the baby
    ("kavya gowda", "4127"),
    ("ಕಾವ್ಯ ಗೌಡ", "4127"),
    ("सुनीता देवी की विज़िट", "4381"),
])
def test_devanagari_kannada_and_full_names_are_sure(said, want_id):
    m = find(said, PEOPLE)
    assert m.person["id"] == want_id and m.sure


def test_every_beneficiary_has_spoken_names():
    assert all(p["spoken_names"] for p in PEOPLE)
