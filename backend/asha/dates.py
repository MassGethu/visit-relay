"""Relative-date resolution for Hindi and Kannada (research/02 4b and rules 8-13).

Every result says whether it must be read back. Day-only dates, tense-ambiguous
"kal", weekdays and "monne" are always confirmed with a full date.
Durations ("7 mahine ka garbh") are kept as durations and NEVER turned into a
due date or vaccine date: the assistant does not compute schedules.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .numbers import parse_numbers, unit_words
from .text import tokens

DAY = dt.timedelta(days=1)

PAST_MARKERS = {"tha", "thi", "the", "gaya", "gayi", "gaye", "kiya", "kiye", "hua", "hui", "hue",
                "lagwaya", "lagaya", "diya", "di", "aaya", "aayi", "aaye", "mila", "mili", "gayi.",
                "था", "थी", "थे", "गया", "गई", "गए", "किया", "हुआ", "हुई", "लगवाया", "दिया", "आया", "आई",
                "bantu", "ittu", "aaytu", "hogittu", "kottaru", "ಬಂತು", "ಇತ್ತು", "ಆಯ್ತು"}
FUTURE_SUFFIXES = ("ega", "egi", "enge", "unga", "oonga", "ogi", "oge", "ेगा", "ेगी", "ेंगे", "ूँगा", "ूंगा",
                   "beku", "ಬೇಕು", "teeni", "ತೀನಿ", "taare", "ತಾರೆ")
FUTURE_WORDS = {"hoga", "hogi", "lagega", "lagegi", "jaana", "aana", "karna", "jayenge", "aayegi",
                "होगा", "होगी", "लगेगा", "जाना", "आना", "barbeku", "hogbeku"}

HI_REL = {"aaj": 0, "आज": 0, "abhi": 0}
KN_REL = {"indu": 0, "ivattu": 0, "ಇಂದು": 0, "ಇವತ್ತು": 0, "naale": 1, "ನಾಳೆ": 1, "ninne": -1,
          "ನಿನ್ನೆ": -1, "naadiddu": 2, "ನಾಡಿದ್ದು": 2, "monne": -2, "ಮೊನ್ನೆ": -2}
EN_REL = {"today": 0, "tomorrow": 1, "yesterday": -1}
TENSE_REL = {"kal": 1, "कल": 1, "parson": 2, "parso": 2, "परसों": 2}

WEEKDAYS = {}
for i, names in enumerate([
        ("somvaar", "somvar", "सोमवार", "somavaara", "ಸೋಮವಾರ", "monday"),
        ("mangalvaar", "mangalvar", "मंगलवार", "mangalavaara", "ಮಂಗಳವಾರ", "tuesday"),
        ("budhvaar", "budhvar", "बुधवार", "budhavaara", "ಬುಧವಾರ", "wednesday"),
        ("guruvaar", "guruvar", "गुरुवार", "brihaspativaar", "बृहस्पतिवार", "guruvaara", "ಗುರುವಾರ", "thursday"),
        ("shukravaar", "shukravar", "शुक्रवार", "shukravaara", "ಶುಕ್ರವಾರ", "friday"),
        ("shanivaar", "shanivar", "शनिवार", "shanivaara", "ಶನಿವಾರ", "saturday"),
        ("ravivaar", "ravivar", "itvaar", "रविवार", "इतवार", "bhaanuvaara", "ಭಾನುವಾರ", "ravivaara",
         "ರವಿವಾರ", "sunday")]):
    for n in names:
        WEEKDAYS[n] = i

MONTHS = {}
for i, names in enumerate([
        ("january", "janvari", "जनवरी", "janavari", "ಜನವರಿ", "jan"),
        ("february", "farvari", "फरवरी", "febravari", "ಫೆಬ್ರವರಿ", "feb"),
        ("march", "maarch", "मार्च", "ಮಾರ್ಚ್"), ("april", "aprail", "अप्रैल", "epril", "ಏಪ್ರಿಲ್"),
        ("may", "mai", "मई", "me", "ಮೇ"), ("june", "joon", "जून", "ಜೂನ್"),
        ("july", "julaai", "जुलाई", "julai", "ಜುಲೈ"), ("august", "agast", "अगस्त", "aagast", "ಆಗಸ್ಟ್"),
        ("september", "sitambar", "सितंबर", "septembar", "ಸೆಪ್ಟೆಂಬರ್"),
        ("october", "aktoobar", "अक्टूबर", "aktobar", "ಅಕ್ಟೋಬರ್"),
        ("november", "navambar", "नवंबर", "navembar", "ನವೆಂಬರ್", "nov"),
        ("december", "disambar", "दिसंबर", "disembar", "ಡಿಸೆಂಬರ್", "dec")], start=1):
    for n in names:
        MONTHS[n] = i

DAY_ONLY = {"tareekh", "taareekh", "tarikh", "तारीख", "taareekhu", "ತಾರೀಖು", "tareek"}
NEXT = {"agle", "agla", "agli", "अगले", "mundina", "ಮುಂದಿನ", "next"}
LAST = {"pichhle", "pichhla", "pichle", "पिछले", "kaleda", "hoda", "ಕಳೆದ", "ಹೋದ", "last"}
THIS = {"is", "इस", "ee", "ಈ", "this"}
WEEK = {"hafte", "hafta", "हफ्ते", "vaara", "ವಾರ", "week"}
MONTH = {"mahine", "mahina", "महीने", "tingalu", "tingala", "ತಿಂಗಳು", "month"}
DAYS = {"din", "दिन", "dina", "dinada", "ದಿನ", "days", "day"}
AFTER = {"baad", "बाद", "mundhe", "ಮುಂದೆ", "later", "after"}
BEFORE = {"pehle", "पहले", "hinde", "ಹಿಂದೆ", "ago", "before"}
DURATION_CONTEXT = {"garbh", "गर्भ", "pregnant", "garbhini", "ಗರ್ಭಿಣಿ", "ka", "ki", "ke", "aagide", "aaytu"}


@dataclass
class DateResult:
    kind: str                       # "date" | "range" | "duration" | "ambiguous"
    value: dt.date | tuple | None   # date, (start, end), or ("months"|"weeks"|"days", n)
    confirm: bool                   # must be read back as a full date before saving
    reason: str = ""


def tense(words: list[str]) -> int:
    """+1 future, -1 past, 0 unknown."""
    if any(w in FUTURE_WORDS or w.endswith(FUTURE_SUFFIXES) for w in words):
        return 1
    if any(w in PAST_MARKERS for w in words):
        return -1
    return 0


def resolve(text: str, today: dt.date) -> DateResult | None:
    words = [t.text for t in tokens(text)]
    direction = tense(words)

    # durations first: "7 mahine ka garbh", "3 hafte ka bachcha", "X tingalu"
    for n in parse_numbers(text):
        unit = words[n.end + 1] if n.end + 1 < len(words) else ""
        tail = words[n.end + 2: n.end + 4]
        if unit in MONTH | WEEK and (set(tail) & DURATION_CONTEXT or not tail):
            kind = "months" if unit in MONTH else "weeks"
            if not (set(tail) & (AFTER | BEFORE)):
                return DateResult("duration", (kind, n.value), False, "duration, not a date")
        if unit in DAYS and tail[:1] and tail[0] in AFTER | BEFORE:
            sign = 1 if tail[0] in AFTER else -1
            return DateResult("date", today + sign * int(n.value) * DAY, False)

    for w in words:
        for table in (HI_REL, KN_REL, EN_REL):
            if w in table:
                approx = w in {"monne", "ಮೊನ್ನೆ"}
                return DateResult("date", today + table[w] * DAY, approx,
                                  "monne can mean 'a few days ago'" if approx else "")
        if w in TENSE_REL:
            if direction == 0:
                return DateResult("ambiguous", None, True, f"'{w}' needs tense: ask which day")
            return DateResult("date", today + direction * TENSE_REL[w] * DAY, False)

    # full date: "15 march", "march 15", "15 march 2026", "teen tareekh chaar mahina"
    nums = parse_numbers(text)
    month = next((MONTHS[w] for w in words if w in MONTHS and w not in {"me", "mai"}), None)
    if month is None and any(w in {"mai", "me", "मई"} for w in words) and nums:
        month = 5  # accept "mai" as May only next to a day number (research/02 note)
    if month and nums:
        day = int(next((n.value for n in nums if 1 <= n.value <= 31), 0))
        year = int(next((n.value for n in nums if n.value >= 2000), today.year))
        if day:
            try:
                return DateResult("date", dt.date(year, month, day), True)
            except ValueError:
                return DateResult("ambiguous", None, True, "no such date")

    if any(w in DAY_ONLY for w in words) or _ordinal_day(words):
        day = _ordinal_day(words) or next((int(n.value) for n in nums if 1 <= n.value <= 31), None)
        if day:
            return DateResult("date", _nearest_day(today, day, direction or 1), True,
                              "day-only date: read back with the month")

    for i, w in enumerate(words):
        if w in WEEKDAYS:
            target = WEEKDAYS[w]
            step = -1 if direction < 0 else 1
            d = today + step * DAY
            while d.weekday() != target:
                d += step * DAY
            return DateResult("date", d, True, "weekday: read back the date")

    for i, w in enumerate(words):
        if w in WEEK | MONTH and i > 0 and words[i - 1] in NEXT | LAST | THIS:
            off = 1 if words[i - 1] in NEXT else -1 if words[i - 1] in LAST else 0
            if w in WEEK:
                monday = today - today.weekday() * DAY + off * 7 * DAY
                return DateResult("range", (monday, monday + 6 * DAY), True, "a week, not a day")
            m = today.month + off
            y = today.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            first = dt.date(y, m, 1)
            nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
            return DateResult("range", (first, nxt - DAY), True, "a month, not a day")
    return None


def _ordinal_day(words: list[str]) -> int | None:
    """Kannada ordinal day: hadinaidane / ಹದಿನೈದನೇ = 15th (cardinal minus final u, plus -ane)."""
    units = unit_words()
    for w in words:
        for suffix, add in (("ane", "u"), ("ನೇ", "ು")):
            if w.endswith(suffix) and (w[: -len(suffix)] + add) in units:
                n = units[w[: -len(suffix)] + add]
                if 1 <= n <= 31:
                    return n
    return None


def _nearest_day(today: dt.date, day: int, direction: int) -> dt.date:
    y, m = today.year, today.month
    for _ in range(13):
        try:
            d = dt.date(y, m, day)
        except ValueError:
            d = None
        if d and ((direction > 0 and d >= today) or (direction < 0 and d <= today)):
            return d
        m += direction
        if m == 13:
            y, m = y + 1, 1
        elif m == 0:
            y, m = y - 1, 12
    raise ValueError(day)
