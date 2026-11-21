import datetime as dt

import pytest

from asha.dates import resolve

FRI = dt.date(2026, 11, 13)


@pytest.mark.parametrize("text,expected,confirm", [
    ("kal teeka lagega", dt.date(2026, 11, 14), False),
    ("kal bleeding hua tha", dt.date(2026, 11, 12), False),
    ("parson aayegi", dt.date(2026, 11, 15), False),
    ("naale", dt.date(2026, 11, 14), False),
    ("ninne", dt.date(2026, 11, 12), False),
    ("monne", dt.date(2026, 11, 11), True),
    ("15 tareekh ko aana hai", dt.date(2026, 11, 15), True),
    ("2 tareekh", dt.date(2026, 12, 2), True),
    ("hadinaidane taareekhu", dt.date(2026, 11, 15), True),
    ("somvaar ko aana hai", dt.date(2026, 11, 16), True),
    ("3 din baad", dt.date(2026, 11, 16), False),
    ("20 november", dt.date(2026, 11, 20), True),
])
def test_dates(text, expected, confirm):
    r = resolve(text, FRI)
    assert r.kind == "date" and r.value == expected and r.confirm == confirm


def test_kal_without_tense_must_be_asked():
    r = resolve("kal teeka", FRI)
    assert r.kind == "ambiguous" and r.confirm


def test_week_is_a_range():
    r = resolve("agle hafte", FRI)
    assert r.kind == "range" and r.value == (dt.date(2026, 11, 16), dt.date(2026, 11, 22))


def test_pregnancy_months_stay_a_duration():
    r = resolve("7 mahine ka garbh", FRI)
    assert r.kind == "duration" and r.value == ("months", 7)
