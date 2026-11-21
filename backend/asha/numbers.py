"""Spoken-number parser for Hindi, Kannada and English (research/02, parsing rules 2-7, 14).

Prisma v3.0 with format=codemix returns numbers as native words, so the
normaliser must read "do point aath", "eraduvare", "ek sau bees by assi".

Ranges in PLAUSIBLE are validation guards for speech-recognition errors only.
They never interpret her health.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache

from .text import DATA, tokens

PLAUSIBLE = {  # research/02 rule 6
    "weight_newborn": (0.5, 6.0), "weight_mother": (25.0, 150.0), "hb": (3.0, 20.0),
    "systolic": (60, 250), "diastolic": (30, 150), "temperature_f": (93.0, 108.0),
    "temperature_c": (34.0, 42.0), "breaths_per_min": (10, 120),
}

ENGLISH = {w: n for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
ENGLISH.update({"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
                "seventy": 70, "eighty": 80, "ninety": 90})
# Colloquial and alternative spellings (research/02 rule 2 and the 4c variant notes).
VARIANTS = {"ond": 1, "erad": 2, "aid": 5, "ent": 8, "chhe": 6, "chhah": 6, "chah": 6, "che": 6,
            "chhaha": 6, "zero": 0, "jiro": 0, "shunya": 0, "sunya": 0, "ikavan": 51,
            "baanve": 92, "bayanve": 92, "unaasi": 79, "nabbe": 90, "navve": 90,
            "छः": 6, "इकावन": 51, "बयानवे": 92, "उनासी": 79, "नव्वे": 90, "ज़ीरो": 0, "जीरो": 0}
HUNDRED = {"sau", "sou", "सौ", "nooru", "noora", "ನೂರು", "ನೂರ", "hundred"}
THOUSAND = {"hazaar", "hazar", "hajaar", "hajar", "हज़ार", "हजार", "saavira", "saavirada",
            "savira", "ಸಾವಿರ", "ಸಾವಿರದ", "thousand"}
LAKH = {"laakh", "lakh", "लाख", "laksha", "ಲಕ್ಷ"}
KN_HUNDREDS = {"innooru": 200, "munnooru": 300, "naanooru": 400, "ainooru": 500, "aarunooru": 600,
               "elunooru": 700, "entunooru": 800, "ombainooru": 900, "ಇನ್ನೂರು": 200,
               "ಮುನ್ನೂರು": 300, "ನಾನೂರು": 400, "ಐನೂರು": 500, "ಆರುನೂರು": 600, "ಏಳುನೂರು": 700,
               "ಎಂಟುನೂರು": 800, "ಒಂಬೈನೂರು": 900}
KN_HUNDREDS.update({k[:-1] + "a": v for k, v in list(KN_HUNDREDS.items()) if k.endswith("u")})
KN_HUNDREDS.update({k[:-1] + "ರ": v for k, v in list(KN_HUNDREDS.items()) if k.endswith("ರು")})
POINT = {"point", "poinT", "pt", "पॉइंट", "पॉइन्ट", "प्वाइंट", "दशमलव", "ಪಾಯಿಂಟ್", "ದಶಮಾಂಶ", "dashamlav"}
# Fractions that stand alone and can scale: "dhai sau" = 250.
FRACTION_WORDS = {"dedh": 1.5, "dedha": 1.5, "डेढ़": 1.5, "dhai": 2.5, "dhaai": 2.5, "ढाई": 2.5,
                  "paav": 0.25, "पाव": 0.25, "aadha": 0.5, "adha": 0.5, "आधा": 0.5,
                  "paun": 0.75, "पौन": 0.75, "ardha": 0.5, "ಅರ್ಧ": 0.5, "kaal": 0.25, "kaalu": 0.25,
                  "ಕಾಲು": 0.25, "mukkaal": 0.75, "mukkaalu": 0.75, "ಮುಕ್ಕಾಲು": 0.75}
PREFIX = {"sava": 0.25, "savaa": 0.25, "सवा": 0.25, "saadhe": 0.5, "sadhe": 0.5, "saade": 0.5,
          "साढ़े": 0.5, "साढे": 0.5, "paune": -0.25, "पौने": -0.25}
REPAIR = {"nahi", "nahin", "galat", "sorry", "matlab", "illa", "alla", "no", "नहीं", "गलत", "ಅಲ್ಲ", "ಇಲ್ಲ"}


@lru_cache(maxsize=1)
def unit_words() -> dict[str, int]:
    """0-100 from data/numbers.tsv (research/02 4c) plus English and spelling variants."""
    words: dict[str, int] = {}
    with open(DATA / "numbers.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            n = int(row["n"])
            for col in ("hi_script", "hi_roman", "kn_script", "kn_roman"):
                words[row[col].strip().lower()] = n
    words.update(ENGLISH)
    words.update(VARIANTS)
    for w in ("sau", "nooru", "सौ", "ನೂರು"):
        words.pop(w, None)  # 100 is a scale word here
    return words


def _kn_fraction_suffix(word: str) -> float | None:
    """eraduvare = 2.5, onduukaalu = 1.25, ಎರಡೂವರೆ = 2.5 (counts up from X)."""
    units = unit_words()
    for suffix, add in (("vare", 0.5), ("ವರೆ", 0.5), ("kaalu", 0.25), ("ಕಾಲು", 0.25)):
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            base = word[: -len(suffix)]
            for cand in (base, re.sub(r"(uu|oo|u)$", "u", base), re.sub(r"(uu|oo)$", "", base) + "u",
                         base[:-1] + "ು" if base.endswith("ೂ") else base):
                if cand in units:
                    return units[cand] + add
    return None


@dataclass
class Number:
    value: float
    start: int          # token index
    end: int
    low_confidence: bool = False
    digits: str = ""    # the digit string as spoken, for IDs ("nau aath" -> "98")


def _unit(word: str) -> float | None:
    if word.replace(".", "", 1).isdigit():
        return float(word)
    units = unit_words()
    if word in units:
        return units[word]
    # Kannada joining vowel before a fraction word: "eradoo mukkaalu", "ಎರಡೂ ಮುಕ್ಕಾಲು"
    for cand in (re.sub(r"(oo|uu)$", "u", word), word[:-1] + "ು" if word.endswith("ೂ") else ""):
        if cand in units:
            return units[cand]
    return folded_units().get(fold_spelling(word)) if word.isascii() else None


def fold_spelling(word: str) -> str:
    """Roman Hindi is spelt many ways: "chalis" / "chaalees", "pachas" / "pachaas"."""
    for long, short in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("w", "v")):
        word = word.replace(long, short)
    return word


@lru_cache(maxsize=1)
def folded_units() -> dict[str, int]:
    out: dict[str, int] = {}
    for w, n in unit_words().items():
        if w.isascii():
            out.setdefault(fold_spelling(w), n)
    return out


TRAILING_FRACTION = {"mukkaalu": 0.75, "mukkaal": 0.75, "ಮುಕ್ಕಾಲು": 0.75, "kaalu": 0.25,
                     "kaal": 0.25, "ಕಾಲು": 0.25, "vare": 0.5, "ವರೆ": 0.5}


def parse_numbers(text: str) -> list[Number]:
    """All numbers in a transcript, in order, with token spans."""
    toks = [t.text for t in tokens(text)]
    out: list[Number] = []
    i = 0
    while i < len(toks):
        n = _parse_at(toks, i)
        if n is None:
            i += 1
            continue
        out.append(n)
        i = n.end + 1
    return out


def _parse_at(toks: list[str], i: int) -> Number | None:
    w = toks[i]
    start = i
    offset = 0.0
    if w in PREFIX and i + 1 < len(toks):
        offset = PREFIX[w]
        i += 1
        w = toks[i]
        if _unit(w) is None and w not in HUNDRED | THOUSAND:
            return None
    if w in FRACTION_WORDS and i + 1 < len(toks) and toks[i + 1] in HUNDRED | THOUSAND:
        scale = 100 if toks[i + 1] in HUNDRED else 1000
        return Number(FRACTION_WORDS[w] * scale, start, i + 1)
    if w in FRACTION_WORDS:
        return Number(FRACTION_WORDS[w], start, i)
    kn = _kn_fraction_suffix(w)
    if kn is not None:
        return Number(kn, start, i)
    if w not in KN_HUNDREDS and _unit(w) is None and w not in HUNDRED:
        return None

    total, current, j, last_was_unit, digits = 0.0, 0.0, i, False, ""
    while j < len(toks):
        t = toks[j]
        u = _unit(t)
        if t in KN_HUNDREDS:
            if last_was_unit:
                break
            current += KN_HUNDREDS[t]
            last_was_unit = False
        elif t in HUNDRED:
            current = (current or 1) * 100
            last_was_unit = False
        elif t in THOUSAND or t in LAKH:
            total += (current or 1) * (1000 if t in THOUSAND else 100000)
            current, last_was_unit = 0.0, False
        elif t == "and" and j > i and toks[j - 1] in {"hundred", "thousand"} \
                and j + 1 < len(toks) and toks[j + 1] in ENGLISH:
            pass  # "hundred and ten" is one number, not a BP pair
        elif u is not None and "." in t:
            if last_was_unit:
                break
            current += u
            last_was_unit = True
        elif u is not None:
            # English "fifty two": a ten followed by a unit; otherwise unit+unit ends the number
            prev = toks[j - 1] if j > i else ""
            if last_was_unit and not (prev in ENGLISH and ENGLISH[prev] % 10 == 0
                                      and ENGLISH[prev] >= 20 and t in ENGLISH and ENGLISH[t] < 10):
                break
            current += u
            last_was_unit = True
            digits += t if t.isdigit() else ""
        else:
            break
        j += 1
    end = j - 1
    value = total + current
    low = False
    if j < len(toks) and toks[j] in TRAILING_FRACTION and value < 100:
        value += TRAILING_FRACTION[toks[j]]   # Kannada counts up: eradoo mukkaalu = 2.75
        end = j
        j += 1
    if j < len(toks) and toks[j] in POINT:
        dec, k = _decimals(toks, j + 1)
        if dec is not None:
            frac, low = dec
            value = float(f"{int(value)}.{frac}")
            end = k
    if offset:
        value += offset
    return Number(value, start, end, low)


def _decimals(toks: list[str], k: int) -> tuple[tuple[str, bool] | None, int]:
    """Digits after "point": each 0-9 word is one digit; a 10-99 word is two (low confidence)."""
    frac, low, end = "", False, k - 1
    while k < len(toks):
        u = _unit(toks[k])
        if u is None or u != int(u) or u >= 100:
            break
        if u >= 10:
            if frac:
                break
            frac, low, end = f"{int(u):02d}", True, k
            break
        frac += str(int(u))
        end = k
        k += 1
    return ((frac, low) if frac else None), end


# ───────────────────────── measurements ─────────────────────────

WEIGHT_WORDS = {"wajan", "vajan", "vazan", "wazan", "weight", "tooka", "ತೂಕ", "वजन", "वज़न"}
KILO = {"kilo", "kilos", "kg", "kgs", "kilogram", "kilograms", "kejee", "kiloo", "किलो", "ಕಿಲೋ", "ಕೆಜಿ"}
GRAM = {"gram", "graam", "gm", "grams", "ग्राम", "ಗ್ರಾಂ"}
BP_WORDS = {"bp", "बीपी", "ಬಿಪಿ", "pressure"}
BY = {"by", "over", "बाई", "ಬೈ", "upon"}
HB_WORDS = {"hb", "hemoglobin", "haemoglobin", "हीमोग्लोबिन", "एचबी", "ಹಿಮೋಗ್ಲೋಬಿನ್"}
TEMP_WORDS = {"temperature", "temp", "tapman", "taapmaan", "तापमान", "degree", "digri", "ಡಿಗ್ರಿ", "डिग्री"}
BREATH_WORDS = {"saans", "breath", "breathing", "usiru", "ಉಸಿರು", "साँस", "सांस"}
TEMP_UNITS = {"celsius": "C", "fahrenheit": "F", "centigrade": "C"}


def extract_measurements(text: str, subject: str = "mother") -> dict:
    """weight_kg, hb, bp, temperature, breaths_per_min, plus 'doubts' for out-of-range values.

    A number followed by a repair word ("2.6 nahi nahi 2.8") is dropped: her last
    value wins. Returns {"doubts": [(field, value, reason)]} alongside the values.
    """
    text = re.sub(r"\bb[.\s]+p\b", "bp", text, flags=re.IGNORECASE)
    text = re.sub(r"\bh[.\s]+b\b", "hb", text, flags=re.IGNORECASE)
    toks = [t.text for t in tokens(text)]
    parsed = parse_numbers(text)
    nums = [n for n in parsed
            if toks[n.end + 1:n.end + 3] not in (["year", "old"], ["years", "old"])
            and not (n.end + 1 < len(toks) and toks[n.end + 1] in REPAIR
                     and any(m.start > n.end for m in parsed))]
    out: dict = {"doubts": []}

    def near(keywords: set[str], n: Number, before: int = 4) -> bool:
        lo = max(0, n.start - before)
        return any(t in keywords for t in toks[lo:n.start])

    def distance(keywords: set[str], n: Number, before: int = 4) -> int | None:
        """Words between the number and the nearest keyword before it (within `before`)."""
        for d in range(1, before + 1):
            if n.start - d >= 0 and toks[n.start - d] in keywords:
                return d
        return None

    used: set[int] = set()
    for idx, n in enumerate(nums):
        nxt = toks[n.end + 1] if n.end + 1 < len(toks) else ""
        # BP: "X by Y" or two numbers after "BP"
        if idx in used:
            continue
        temp_unit_at = n.end + (2 if nxt in {"degree", "degrees"} else 1)
        spoken_unit = TEMP_UNITS.get(toks[temp_unit_at]) if temp_unit_at < len(toks) else None
        if idx + 1 < len(nums) and (
            (nxt in BY and nums[idx + 1].start == n.end + 2)
            or (near(BP_WORDS, n) and nums[idx + 1].start == n.end + 1)
        ):
            sys_, dia = n.value, nums[idx + 1].value
            # "bees assi" after BP = 120/80. Research/02 rule 7 says "second less than the
            # first"; that only holds after expansion (80 < 120), so compare with sys + 100.
            if (sys_ < dia < 100 and nxt not in BY and near(BP_WORDS, n)
                    and not toks[n.start].isdigit()):
                sys_ += 100
                out["doubts"].append(("bp", (int(sys_), int(dia)), "hundreds were dropped"))
            out["bp"] = (int(sys_), int(dia))
            used |= {idx, idx + 1}
            continue
        # Several field words may sit before a number ("wajan baavan kilo, hb saadhe nau"):
        # the nearest one decides. A unit right after the number counts as distance 0.
        dists = {"weight_kg": 0 if nxt in KILO else distance(WEIGHT_WORDS, n),
                 "hb": distance(HB_WORDS, n),
                 "bp_partial": distance(BP_WORDS, n),
                 "temperature": 0 if nxt in TEMP_WORDS or spoken_unit else distance(TEMP_WORDS, n),
                 "breaths_per_min": distance(BREATH_WORDS, n, before=6)}
        found = {f: d for f, d in dists.items() if d is not None}
        field_ = min(found, key=found.get) if found else None      # ties: dict order above
        if field_ == "weight_kg":
            value = n.value
            after = n.end + 2
            if nxt in KILO and idx + 1 < len(nums) and nums[idx + 1].start == after:
                grams = nums[idx + 1]
                gnext = toks[grams.end + 1] if grams.end + 1 < len(toks) else ""
                if grams.value < 1000 and (gnext in GRAM or subject == "newborn" or gnext == ""):
                    value += grams.value / 1000      # "do kilo aath sau (gram)" = 2.8
                    used.add(idx + 1)
            out["weight_kg"] = round(value, 3)
            if n.low_confidence:
                out["doubts"].append(("weight_kg", value, "decimal heard as a two-digit word"))
        elif field_ == "hb":
            out["hb"] = n.value
        elif field_ == "bp_partial":
            out["bp_partial"] = n.value
        elif field_ == "temperature":
            unit = spoken_unit or ("F" if n.value > 50 else "C")
            out["temperature"] = (n.value, unit)
        elif field_ == "breaths_per_min":
            out["breaths_per_min"] = int(n.value)

    _check_ranges(out, subject)
    return out


def _check_ranges(out: dict, subject: str) -> None:
    def outside(key, v):
        lo, hi = PLAUSIBLE[key]
        return not lo <= v <= hi
    if "weight_kg" in out:
        key = "weight_newborn" if subject == "newborn" else "weight_mother"
        if outside(key, out["weight_kg"]):
            out["doubts"].append(("weight_kg", out["weight_kg"], "outside plausible range"))
    if "hb" in out and outside("hb", out["hb"]):
        out["doubts"].append(("hb", out["hb"], "outside plausible range"))
    if "bp" in out and (outside("systolic", out["bp"][0]) or outside("diastolic", out["bp"][1])):
        out["doubts"].append(("bp", out["bp"], "outside plausible range"))
    if "temperature" in out:
        v, unit = out["temperature"]
        if outside("temperature_f" if unit == "F" else "temperature_c", v):
            out["doubts"].append(("temperature", out["temperature"], "outside plausible range"))


# ───────────────────────── IDs ─────────────────────────

def parse_digit_string(text: str) -> str:
    """IDs and phone numbers: keep every digit, never compose ("nau aath" -> "98", not 98 as a number).

    Accepts "double 5" / "triple 0" and Hindi "do baar"-free forms. Rule 14.
    """
    toks = [t.text for t in tokens(text)]
    out, repeat = "", 1
    for t in toks:
        if t in {"double", "dabal", "डबल"}:
            repeat = 2
            continue
        if t in {"triple", "tripal", "ट्रिपल"}:
            repeat = 3
            continue
        if t.isdigit():
            out += t * repeat if len(t) == 1 else t
        else:
            u = unit_words().get(t)
            if u is not None and u < 10:
                out += str(u) * repeat
        repeat = 1
    return out


ID_LENGTHS = {"mobile": 10, "aadhaar": 12}   # others are UNVERIFIED in research/02


def valid_id(kind: str, digits: str) -> bool:
    need = ID_LENGTHS.get(kind)
    return digits.isdigit() and (need is None or len(digits) == need)
