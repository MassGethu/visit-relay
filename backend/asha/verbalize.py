"""Numbers, IDs and dates as words for Timbre (research/02 4c, rule 15).

Gnani's docs disagree on whether Timbre normalises numbers itself, Kannada
normalisation is "under refinement", and "23/06" without a year is read as a
fraction. So every number is written out here and `language` is always set.

Kannada 21-99 compounds and the hundreds combining form are rule-generated
(UNSOURCED-linguistic in research/02): check them by ear in Timbre.
"""
from __future__ import annotations

import csv
import datetime as dt
from functools import lru_cache

from .text import DATA

POINT = {"hi": "पॉइंट", "kn": "ಪಾಯಿಂಟ್", "en": "point"}
ZERO_DIGIT = {"hi": "ज़ीरो", "kn": "ಸೊನ್ನೆ", "en": "zero"}  # spoken zero in digit strings
HUNDRED = {"hi": "सौ", "en": "hundred"}
THOUSAND = {"hi": "हज़ार", "kn": "ಸಾವಿರ", "en": "thousand"}
KN_HUNDREDS = ["", "ನೂರು", "ಇನ್ನೂರು", "ಮುನ್ನೂರು", "ನಾನೂರು", "ಐನೂರು", "ಆರುನೂರು", "ಏಳುನೂರು",
               "ಎಂಟುನೂರು", "ಒಂಬೈನೂರು"]
MONTHS = {
    "hi": ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर",
           "नवंबर", "दिसंबर"],
    "kn": ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್",
           "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
}
WEEKDAYS = {
    "hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
    "kn": ["ಸೋಮವಾರ", "ಮಂಗಳವಾರ", "ಬುಧವಾರ", "ಗುರುವಾರ", "ಶುಕ್ರವಾರ", "ಶನಿವಾರ", "ಭಾನುವಾರ"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}
EN_UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
            "fifteen sixteen seventeen eighteen nineteen").split()
EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
ID_GROUPS = {"mobile": (3, 3, 4), "aadhaar": (4, 4, 4)}  # Gnani's conventions; others in 4s


@lru_cache(maxsize=1)
def _table() -> dict[str, list[str]]:
    hi, kn = [""] * 101, [""] * 101
    with open(DATA / "numbers.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            n = int(row["n"])
            hi[n], kn[n] = row["hi_script"].strip(), row["kn_script"].strip()
    return {"hi": hi, "kn": kn}


def _en_below_100(n: int) -> str:
    if n < 20:
        return EN_UNITS[n]
    return EN_TENS[n // 10] + ("" if n % 10 == 0 else " " + EN_UNITS[n % 10])


def integer(n: int, lang: str) -> str:
    if n < 0:
        raise ValueError("negative numbers are never spoken by this app")
    if lang == "en":
        below = _en_below_100
    else:
        table = _table()[lang]
        below = lambda k: table[k]
    if n < 100:
        return below(n)
    parts = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        if lang == "kn":
            # "ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತಾರು" for 2026, "ಎರಡು ಸಾವಿರ" for 2000
            word = THOUSAND["kn"] + ("ದ" if rest else "")
            parts.append((integer(thousands, lang) + " " + word) if thousands > 1 else word)
        else:
            parts.append(integer(thousands, lang) + " " + THOUSAND[lang])
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        if lang == "kn":
            word = KN_HUNDREDS[hundreds]
            parts.append(word[:-1] if rest else word)   # combining form: ನೂರ ಇಪ್ಪತ್ತು = 120
        else:
            parts.append(integer(hundreds, lang) + " " + HUNDRED[lang])
    if rest:
        parts.append(below(rest))
    return " ".join(parts)


def number(value: float, lang: str) -> str:
    """2.8 -> "दो पॉइंट आठ"; 2.85 -> "दो पॉइंट आठ पाँच" (digits after the point, never "pachaasi")."""
    text = f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    whole, _, frac = text.partition(".")
    words = integer(int(whole), lang)
    if frac:
        words += " " + POINT[lang] + " " + " ".join(digit(int(d), lang) for d in frac)
    return words


def digit(d: int, lang: str) -> str:
    return ZERO_DIGIT[lang] if d == 0 else integer(d, lang)


def digits(s: str, lang: str, kind: str = "") -> str:
    """IDs read one digit at a time in groups, with commas to force pauses.

    No "double" compression outside English (Gnani: only English compresses).
    """
    s = "".join(ch for ch in s if ch.isdigit())
    sizes = ID_GROUPS.get(kind)
    groups, i = [], 0
    if sizes and sum(sizes) == len(s):
        for size in sizes:
            groups.append(s[i:i + size])
            i += size
    else:
        groups = [s[j:j + 4] for j in range(0, len(s), 4)]
    return ", ".join(" ".join(digit(int(c), lang) for c in g) for g in groups)


def date(d: dt.date, lang: str, weekday: bool = True, year: bool = False) -> str:
    """Hindi: day month (year). Kannada: month day, year. Never a bare dd/mm."""
    wd = WEEKDAYS[lang][d.weekday()] + ", " if weekday else ""
    if lang == "kn":
        text = f"{MONTHS['kn'][d.month - 1]} {integer(d.day, 'kn')}"
    elif lang == "en":
        text = f"{integer(d.day, 'en')} {MONTHS['en'][d.month - 1]}"
    else:
        text = f"{integer(d.day, 'hi')} {MONTHS['hi'][d.month - 1]}"
    if year:
        text += (", " if lang == "kn" else " ") + integer(d.year, lang)
    return wd + text
