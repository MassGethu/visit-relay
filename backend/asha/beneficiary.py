"""Find the beneficiary she means from a spoken ID or name (fuzzy). Below SURE, the agent asks to confirm.

    m = find("ID chaar ek do saat", people)   -> Match(person=..., score=100, by="id")
    if not m.sure: speaker.confirm_beneficiary(m.person)

IDs are spoken digit by digit, so any script's number words work. Names are matched in Latin script
only: a name Prisma writes in Devanagari or Kannada script will not match (use the ID or the picker).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher

from .numbers import parse_digit_string
from .text import DATA, tokens

SURE = 90                       # the guide's threshold: below this, ask "Kya aap {name}, ID {id} ...?"
MIN_ID_DIGITS = 3
MIN_SCORE = 70                  # below this nobody fits: say nothing rather than guess
FILLER = {"ka", "ki", "ke", "ko", "ji", "didi", "bhabhi", "aunty", "id", "naam", "name", "visit",
          "hai", "hain", "ho", "wala", "wali", "of", "the", "for", "is", "ghar", "mane"}


@dataclass(frozen=True)
class Match:
    person: dict
    score: int                  # 0-100
    by: str                     # "id" | "name"

    @property
    def sure(self) -> bool:
        return self.score >= SURE


def load_people() -> list[dict]:
    return json.loads((DATA / "beneficiaries.json").read_text("utf-8"))


def _ratio(a: str, b: str) -> int:
    return round(100 * SequenceMatcher(None, a, b).ratio())


def _by_id(digits: str, people: list[dict]) -> list[tuple[int, dict]]:
    return [(_ratio(digits, str(p["id"])), p) for p in people]


def _by_name(words: list[str], people: list[dict]) -> list[tuple[int, dict]]:
    """Each spoken word scores against its best name word; the person's score is the average."""
    out = []
    for p in people:
        name = [t.text for t in tokens(p["name"])]
        out.append((round(sum(max(_ratio(w, n) for n in name) for w in words) / len(words)), p))
    return out


def find(text: str, people: list[dict]) -> Match | None:
    """Best match for her words, or None if she said neither an ID nor a name word."""
    if not people:
        return None
    digits = parse_digit_string(text)
    if len(digits) >= MIN_ID_DIGITS:
        scored, by = _by_id(digits, people), "id"
    else:
        words = [t.text for t in tokens(text) if t.text not in FILLER and not t.text.isdigit()]
        if not words:
            return None
        scored, by = _by_name(words, people), "name"
    scored.sort(key=lambda sp: -sp[0])
    best, person = scored[0]
    if best < MIN_SCORE:
        return None
    if len(scored) > 1 and scored[1][0] == best:
        best = min(best, SURE - 1)          # two people fit equally well: never pick one silently
    return Match(person, best, by)
