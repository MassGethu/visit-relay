import datetime as dt

import pytest

from asha import verbalize as v
from asha.guard import guard, violations
from asha.speak import TEMPLATES, Speaker


def test_numbers_in_words():
    assert v.number(2.8, "hi") == "दो पॉइंट आठ"
    assert v.number(2.85, "hi") == "दो पॉइंट आठ पाँच"          # never "pachaasi"
    assert v.integer(120, "hi") == "एक सौ बीस"
    assert v.integer(2026, "hi") == "दो हज़ार छब्बीस"
    assert v.integer(120, "kn") == "ನೂರ ಇಪ್ಪತ್ತು"
    assert v.integer(2026, "kn") == "ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು"
    assert v.number(9.5, "kn") == "ಒಂಬತ್ತು ಪಾಯಿಂಟ್ ಐದು"


def test_ids_grouped_digit_by_digit():
    assert v.digits("9845012345", "hi", "mobile") == "नौ आठ चार, पाँच ज़ीरो एक, दो तीन चार पाँच"


def test_dates_never_bare():
    d = dt.date(2026, 3, 16)
    assert v.date(d, "hi") == "सोमवार, सोलह मार्च"
    assert v.date(d, "kn", year=True) == "ಸೋಮವಾರ, ಮಾರ್ಚ್ ಹದಿನಾರು, ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು"


@pytest.mark.parametrize("bad", [
    "Paracetamol de dijiye", "500 mg do", "din mein do baar goli khaiye", "Isko pneumonia hai",
    "goli khilaiye", "ಮಾತ್ರೆ ಕೊಡಿ", "दवा दीजिए",
])
def test_guard_blocks_treatment_and_diagnosis(bad):
    safe, found = guard(bad, "hi")
    assert found and "ilaaj ya dawa nahi" in safe


def test_every_template_passes_the_guard():
    for key, langs in TEMPLATES.items():
        for lang, text in langs.items():
            assert violations(text) == [], (key, lang)


def test_disclosure_must_come_first():
    s = Speaker("hi")
    with pytest.raises(RuntimeError):
        s.alert("anc_vaginal_bleeding")
    assert s.say("disclosure").startswith("Main AI hoon")
    assert "PHC" in s.alert("anc_vaginal_bleeding")


def test_choice_question_reads_numbers_as_words():
    s = Speaker("hi")
    s.say("disclosure")
    assert s.choice("weight_kg", 28, 2.8, 28) == "Maine अट्ठाईस kilo suna. दो पॉइंट आठ kilo ya अट्ठाईस kilo?"


def test_every_sign_name_passes_guard_in_every_language():
    from asha.danger import load_lexicon
    from asha.guard import violations
    from asha.speak import spoken_sign
    blocked = [(sign, lang) for sign in load_lexicon().signs for lang in ("en", "hi", "kn")
               if violations(spoken_sign(sign, lang))]
    assert blocked == []
