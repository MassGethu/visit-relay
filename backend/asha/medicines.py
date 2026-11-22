"""Medicines already given: what an ASHA, ANM or PHC handed over, read from her own words.

    read("pichli ASHA ne tees IFA goli di thi, calcium bhi")
      -> found  [{"name": "IFA tablets", "count": 30, "by": "another ASHA"},
                 {"name": "Calcium tablets", "count": None, "by": "another ASHA"}]
         denied set()
    read("calcium nahi diya")  -> found [], denied {"Calcium tablets"}

This only RECORDS what she says was given, for the report. It never suggests a medicine or a
dose, and nothing here is spoken: medicine names stay on the screen and in the saved record.
Rules only, so it works in Hindi, Kannada and English without the LLM.
"""
from __future__ import annotations

import re

from .numbers import parse_numbers
from .text import normalize, similar, tokens

# Display name -> spoken / written forms (token tuples). Covers the ASHA drug kit and the
# ANC / PNC / HBYC supplements she hands out, in romanised and native script.
NAMES: dict[str, tuple[tuple[str, ...], ...]] = {
    "IFA tablets": (
        ("ifa",), ("i", "f", "a"), ("आईएफए",), ("आई", "एफ", "ए"), ("ಐಎಫ್ಎ",), ("ಐ", "ಎಫ್", "ಎ"),
        ("iron",), ("आयरन",), ("ಐರನ್",), ("folic",), ("फोलिक",), ("ಫೋಲಿಕ್",),
        ("lohe", "ki"), ("loha", "ki"), ("लोहे", "की"), ("khoon", "ki", "goli"), ("khoon", "badhane"),
        ("खून", "की", "गोली"), ("खून", "बढ़ाने"), ("kabbina",), ("kabbinada",), ("ಕಬ್ಬಿಣ",), ("ಕಬ್ಬಿಣದ",),
    ),
    "Calcium tablets": (
        ("calcium",), ("kalsiyam",), ("कैल्शियम",), ("कैल्सियम",), ("ಕ್ಯಾಲ್ಸಿಯಂ",), ("ಕ್ಯಾಲ್ಶಿಯಂ",),
    ),
    "Deworming (albendazole)": (
        ("albendazole",), ("albendazol",), ("अल्बेंडाजोल",), ("एल्बेंडाजोल",), ("ಆಲ್ಬೆಂಡಜೋಲ್",),
        ("deworming",), ("keede", "ki"), ("keedon", "ki"), ("kide", "ki"), ("कीड़े", "की"), ("कीड़ों", "की"),
        ("pet", "ke", "keede"), ("पेट", "के", "कीड़े"), ("ಜಂತುಹುಳು",), ("jantu", "hulu"), ("jantuhulu",),
    ),
    "ORS": (
        ("ors",), ("o", "r", "s"), ("ओआरएस",), ("ओ", "आर", "एस"), ("ಒಆರ್ಎಸ್",),
        ("jeevan", "rakshak", "ghol"), ("जीवन", "रक्षक", "घोल"),
    ),
    "Zinc tablets": (("zinc",), ("zink",), ("जिंक",), ("ज़िंक",), ("ಜಿಂಕ್",)),
    "Vitamin A": (("vitamin", "a"), ("विटामिन", "ए"), ("ವಿಟಮಿನ್", "ಎ")),
    "Paracetamol": (("paracetamol",), ("पैरासिटामोल",), ("ಪ್ಯಾರಸಿಟಮಾಲ್",)),
}
# Romanised one-word names long enough to forgive an STT spelling slip ("albendajol").
FUZZY = {"calcium": "Calcium tablets", "albendazole": "Deworming (albendazole)",
         "paracetamol": "Paracetamol", "deworming": "Deworming (albendazole)"}

# Who gave it. Any mention of an ASHA in her own note means another ASHA did.
GIVERS = (
    ("another ASHA", {"asha", "aasha", "आशा", "ಆಶಾ"}),
    ("ANM", {"anm", "एएनएम", "ಎಎನ್ಎಂ", "sister", "सिस्टर"}),
    ("PHC / hospital", {"phc", "hospital", "aspatal", "aspataal", "अस्पताल", "ಆಸ್ಪತ್ರೆ", "doctor",
                        "daktar", "डॉक्टर", "ಡಾಕ್ಟರ್"}),
)
NEGATIONS = {"nahi", "nahin", "nai", "नहीं", "नही", "not", "no", "never", "didn't", "didnt", "illa", "ಇಲ್ಲ",
             "band", "बंद", "chhod", "chhoda", "chhodi", "छोड़", "छोड़ी", "stopped"}
QUESTIONS = {"kitni", "kitna", "kaunsi", "kaunsa", "konsi", "kya", "kaise", "should", "which", "how",
             "कितनी", "कितना", "कौनसी", "कौन", "क्या", "कैसे", "ಎಷ್ಟು", "ಯಾವ", "eshtu", "yaava"}
TIME_UNITS = {"din", "dino", "दिन", "days", "day", "mahine", "mahina", "महीने", "महीना", "months", "month",
              "hafte", "हफ्ते", "weeks", "week", "dina", "ದಿನ", "tingalu", "ತಿಂಗಳು"}
MAX_COUNT = 400                      # a 180-day IFA course is the largest pack she hands out
# Clauses: "IFA di, calcium nahi" must not let one "nahi" deny both.
_CLAUSE = re.compile(r"[,;?!।]|\s(?:aur|और|and|but|lekin|लेकिन|par|पर|ಮತ್ತು|matthu|aadre|ಆದರೆ)\s")


def _negated(word: str) -> bool:
    # Kannada negates with a suffix: "kottilla", "ಕೊಟ್ಟಿಲ್ಲ" (not "ಎಲ್ಲ", all).
    return word in NEGATIONS or word.endswith(("illa", "ಿಲ್ಲ"))


def _matches(words: list[str]) -> list[tuple[str, int, int]]:
    """(name, first token, last token) for every medicine named in one clause."""
    out, i = [], 0
    while i < len(words):
        hit = None
        for name, forms in NAMES.items():
            for form in forms:
                if tuple(words[i:i + len(form)]) == form and (hit is None or len(form) > hit[2] - hit[1] + 1):
                    hit = (name, i, i + len(form) - 1)
        if hit is None and words[i].isascii():
            hit = next(((name, i, i) for key, name in FUZZY.items() if len(words[i]) >= 6
                        and similar(words[i], key)), None)
        if hit:
            out.append(hit)
            i = hit[2] + 1
        else:
            i += 1
    return out


def _count(clause: str, words: list[str], start: int, end: int, taken: set[int]) -> int | None:
    """A whole number right before the name, or right after it ("IFA goli tees")."""
    for n in parse_numbers(clause):
        if n.low_confidence or n.value != int(n.value) or not 0 < n.value <= MAX_COUNT:
            continue
        if any(i in taken for i in range(n.start, n.end + 1)):
            continue                     # the "a" of "vitamin a" is not a count
        after = words[n.end + 1] if n.end + 1 < len(words) else ""
        if after in TIME_UNITS:
            continue                     # "30 din" is how long, not how many
        if n.end == start - 1 or start - 1 <= n.start - end <= 3 and n.start > end:
            return int(n.value)
    return None


def _giver(words: set[str]) -> str | None:
    return next((who for who, cues in GIVERS if words & cues), None)


def read(text: str) -> tuple[list[dict], set[str]]:
    """Medicines she says were given (found) and ones she says were not (denied)."""
    all_words = {t.text for t in tokens(text)}
    if "?" in text or all_words & QUESTIONS:
        return [], set()                 # a question is never a record
    by = _giver(all_words)
    found, denied = [], set()
    for clause in _CLAUSE.split(normalize(text)):
        words = [t.text for t in tokens(clause)]
        hits = _matches(words)
        if not hits:
            continue
        if any(_negated(w) for w in words):
            denied.update(name for name, _, _ in hits)
            continue
        taken = {i for _, s, e in hits for i in range(s, e + 1)}
        for name, s, e in hits:
            if name not in {m["name"] for m in found}:
                found.append({"name": name, "count": _count(clause, words, s, e, taken), "by": by})
    return found, denied - {m["name"] for m in found}


def merge(current: list[dict], found: list[dict], denied: set[str]) -> list[dict]:
    """New mentions update count / giver; a later "not given" removes the entry."""
    out = {m["name"]: dict(m) for m in current if m["name"] not in denied}
    for m in found:
        old = out.get(m["name"], {})
        out[m["name"]] = {"name": m["name"], "count": m["count"] or old.get("count"),
                          "by": m["by"] or old.get("by")}
    return list(out.values())
