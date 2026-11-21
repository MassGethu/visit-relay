"""Find the beneficiary she means from a spoken ID or name (fuzzy). Below SURE, the agent asks to confirm.

    m = find("ID chaar ek do saat", people)   -> Match(person=..., score=100, by="id")
    if not m.sure: speaker.confirm_beneficiary(m.person)

IDs are spoken digit by digit, so any script's number words work. Names match the Latin name or any
of the person's "spoken_names" (Devanagari, Kannada), since Prisma writes Hindi in Devanagari.
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
          "hai", "hain", "ho", "wala", "wali", "of", "the", "for", "is", "ghar", "mane",
          "का", "की", "के", "को", "है", "हैं", "जी", "दीदी", "आईडी", "नाम", "विज़िट", "घर", "ಅವರ", "ಮನೆ"}


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


def _by_id(digits: str, people: list[dict]) -> list[tuple[int, float, dict]]:
    return [(_ratio(digits, str(p["id"])), 1.0, p) for p in people]


def _by_name(words: list[str], people: list[dict]) -> list[tuple[int, float, dict]]:
    """Each spoken word scores against its best name word; the person's score is the average,
    taken over whichever spelling of the name (Latin, Devanagari, Kannada) fits best.
    Ties break on coverage: "Kavya Gowda" fits the mother's whole name, only part of the baby's."""
    out = []
    for p in people:
        best = (0, 0.0)
        for spelling in [p["name"], *p.get("spoken_names", [])]:
            name = [t.text for t in tokens(spelling) if t.text not in FILLER]
            per_word = [max((_ratio(w, n), n) for n in name) for w in words]
            score = round(sum(r for r, _ in per_word) / len(words))
            covered = len({n for r, n in per_word if r >= SURE}) / len(name)
            best = max(best, (score, covered))
        out.append((*best, p))
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
    scored.sort(key=lambda sp: (-sp[0], -sp[1]))
    best, _, person = scored[0]
    if best < MIN_SCORE:
        return None
    full_name = scored[0][1] == 1.0 and (len(scored) == 1 or scored[1][1] < 1.0)
    if len(scored) > 1 and scored[1][0] == best and not full_name:
        best = min(best, SURE - 1)          # two people fit equally well: never pick one silently
    return Match(person, best, by)
