import pytest

from asha.numbers import extract_measurements, parse_digit_string, parse_numbers, valid_id


@pytest.mark.parametrize("text,value", [
    ("do point aath", 2.8), ("dhai", 2.5), ("saadhe nau", 9.5), ("paune teen", 2.75),
    ("sava do", 2.25), ("dedh sau", 150), ("dhai sau", 250), ("ek sau bees", 120),
    ("eraduvare", 2.5), ("ombattuvare", 9.5), ("eradoo mukkaalu", 2.75), ("ಎರಡೂ ಮುಕ್ಕಾಲು", 2.75),
    ("onduukaalu", 1.25), ("noora ippattu", 120), ("innooru", 200), ("do hazaar chhabbees", 2026),
    ("eradu saavirada ippattaaru", 2026), ("fifty two point five", 52.5), ("ಎರಡೂವರೆ", 2.5),
    ("दो पॉइंट आठ", 2.8), ("baavan", 52), ("saath", 60), ("saat", 7), ("52", 52), ("2.8", 2.8),
])
def test_single_values(text, value):
    nums = parse_numbers(text)
    assert len(nums) == 1 and nums[0].value == pytest.approx(value)


def test_two_digit_decimal_is_low_confidence():
    n = parse_numbers("do point pachaasi")[0]
    assert n.value == pytest.approx(2.85) and n.low_confidence


@pytest.mark.parametrize("text,subject,key,value", [
    ("baby ka wajan do kilo aath sau", "newborn", "weight_kg", 2.8),
    ("do kilo aath sau gram", "newborn", "weight_kg", 2.8),
    ("baavan kilo paanch sau gram", "mother", "weight_kg", 52.5),
    ("aivatteradu kilo ainooru graam", "mother", "weight_kg", 52.5),
    ("saadhe baavan kilo", "mother", "weight_kg", 52.5),
    ("eradu point entu kilo", "newborn", "weight_kg", 2.8),
    ("BP ek sau bees by assi", "mother", "bp", (120, 80)),
    ("BP noora ippattu by embattu", "mother", "bp", (120, 80)),
    ("hb saadhe nau hai", "mother", "hb", 9.5),
    ("bukhaar ek sau ek point chaar degree", "mother", "temperature", (101.4, "F")),
    ("saans ek minute mein saath", "newborn", "breaths_per_min", 60),
])
def test_measurements(text, subject, key, value):
    m = extract_measurements(text, subject)
    assert m[key] == (pytest.approx(value) if isinstance(value, float) else value)


def test_dropped_hundreds_are_expanded_and_confirmed():
    m = extract_measurements("BP bees assi")
    assert m["bp"] == (120, 80) and m["doubts"][0][0] == "bp"


def test_self_repair_keeps_last_value():
    assert extract_measurements("wajan 2.6 nahi nahi 2.8 kilo", "newborn")["weight_kg"] == 2.8


def test_out_of_range_is_a_doubt_not_a_diagnosis():
    m = extract_measurements("wajan 28 kilo", "newborn")
    assert m["doubts"] == [("weight_kg", 28.0, "outside plausible range")]


def test_ids_keep_every_digit():
    assert parse_digit_string("nau aath chaar double paanch zero") == "984550"
    assert parse_digit_string("ek zero chaar do") == "1042"
    assert valid_id("mobile", "9845012345") and not valid_id("mobile", "98450")


@pytest.mark.parametrize("text, subject, expected", [
    ("wajan baavan kilo, hb saadhe nau", "mother", {"weight_kg": 52.0, "hb": 9.5}),
    ("wajan 52 kilo, hb 9.5", "mother", {"weight_kg": 52.0, "hb": 9.5}),
    ("bukhaar 101 degree, saans 64 per minute", "newborn",
     {"temperature": (101.0, "F"), "breaths_per_min": 64}),
])
def test_nearest_field_word_decides_which_field_a_number_fills(text, subject, expected):
    m = extract_measurements(text, subject)
    assert {k: v for k, v in m.items() if k != "doubts"} == expected


@pytest.mark.parametrize("said, bp", [("BP ek sau chalis by nabbe", (140, 90)),
                                       ("BP ek sau chaalis by nabbe", (140, 90)),
                                       ("BP ek sau pachas by assi", (150, 80))])
def test_bp_with_other_roman_spellings(said, bp):
    assert extract_measurements(said)["bp"] == bp


def test_weight_is_not_overwritten_by_a_bp_reading():
    m = extract_measurements("wajan baavan kilo, BP ek sau chalis by nabbe")
    assert m["weight_kg"] == 52.0 and m["bp"] == (140, 90)


def test_several_measurements_with_spaced_speech_abbreviations():
    m = extract_measurements("B P is 99 over 70, H B is 10, 52 kilograms")
    assert (m["bp"], m["hb"], m["weight_kg"]) == ((99, 70), 10.0, 52.0)


@pytest.mark.parametrize("text", [
    "Patient is two hundred years old with a BP of hundred and ten",
    "Patient has a BP of 110. 40 years old.",
])
def test_spoken_hundreds_and_age_do_not_fill_missing_blood_pressure(text):
    m = extract_measurements(text)
    assert m["bp_partial"] == 110.0
    assert "bp" not in m
