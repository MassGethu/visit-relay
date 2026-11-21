"""Shared text helpers: tokenising code-mixed Hindi / Kannada / English transcripts."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Anything that is not a letter, digit, combining mark or decimal point splits tokens.
_SPLIT = re.compile(r"[^\wऀ-ॿಀ-೿.]+", re.UNICODE)


@dataclass(frozen=True)
class Token:
    text: str      # lower-cased surface form
    index: int     # position in the token list


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = text.translate(str.maketrans("…—–।॥", "     "))
    return text


def tokens(text: str) -> list[Token]:
    out = []
    for raw in _SPLIT.split(normalize(text)):
        raw = raw.strip(".")
        if raw:
            out.append(Token(raw, len(out)))
    return out


def fold(word: str) -> str:
    """Loose spelling key for romanised Indic words, used for fuzzy matching only.

    "kudithilla" and "kudeetilla" both fold to "kuditila"; "khoon" and "kun" match.
    Never use this for numbers: it merges "saat" (7) and "saath" (60).
    """
    w = word.lower()
    for a, b in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"),
                 ("kh", "k"), ("gh", "g"), ("chh", "c"), ("ch", "c"), ("th", "t"),
                 ("dh", "d"), ("bh", "b"), ("ph", "f"), ("sh", "s"), ("w", "v"), ("z", "j")):
        w = w.replace(a, b)
    w = re.sub(r"(.)\1+", r"\1", w)          # doubled letters: "illa" -> "ila"
    if len(w) > 3 and w.endswith("n") and w[-2] in "aeiou":
        w = w[:-1]                            # nasal ending: "nahin" -> "nahi"
    return w


def similar(a: str, b: str) -> bool:
    if a == b:
        return True
    fa, fb = fold(a), fold(b)
    if fa == fb:
        return True
    if min(len(fa), len(fb)) < 4:
        return False
    return SequenceMatcher(None, fa, fb).ratio() >= 0.84
