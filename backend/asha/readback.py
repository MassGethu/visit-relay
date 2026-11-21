"""Clinically gated read-back (PLAN F5, refined by the innovation council).

Prisma gives no confidence score, so doubt comes from what is medically
implausible, contradictory or disputed, not from the recogniser:
  - at most ONE non-safety question per visit, folded into the read-back,
    as a short choice ("28 suna. 2.8 kilo ya 28 kilo?")
  - exactly one safety turn, asking about at most 3 danger signs
  - a clean visit gets zero questions: one summary sentence and "record pakka"
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .numbers import PLAUSIBLE

# Priority of a doubt (lower is asked first).
PRIORITY = {"out_of_range": 0, "contradiction": 1, "id_match": 2, "date": 3, "llm_unsure": 4,
            "low_audio": 5, "approximate": 6}


@dataclass
class Doubt:
    field: str
    value: object
    kind: str
    alternative: object = None   # for a choice question


@dataclass
class ReadbackPlan:
    question: Doubt | None
    safety_signs: list[str]
    unverified: list[str] = field(default_factory=list)  # left for the ANM if unanswered


def _range_key(field_name: str, subject: str) -> str | None:
    if field_name == "weight_kg":
        return "weight_newborn" if subject == "newborn" else "weight_mother"
    return {"hb": "hb"}.get(field_name)


def decimal_shift_alternative(value: float, key: str) -> float | None:
    """28 for a newborn -> 2.8; 520 for a mother -> 52.0. Only if the shifted value is plausible."""
    lo, hi = PLAUSIBLE[key]
    for f in (10, 100, 0.1):
        alt = round(value / f, 2)
        if lo <= alt <= hi:
            return alt
    return None


def find_doubts(record: dict, subject: str, today: dt.date, extras: list[Doubt] = ()) -> list[Doubt]:
    """record: {field: value}, plus optional "_unsure": [...], "_low_audio": [...], "_id_score": int."""
    doubts: list[Doubt] = list(extras)
    for f, v in record.items():
        if f.startswith("_") or v is None:
            continue
        key = _range_key(f, subject)
        if key and isinstance(v, (int, float)):
            lo, hi = PLAUSIBLE[key]
            if not lo <= v <= hi:
                doubts.append(Doubt(f, v, "out_of_range", decimal_shift_alternative(v, key)))
        if f == "next_visit_date" and isinstance(v, dt.date):
            if v < today or (v - today).days > 90:
                doubts.append(Doubt(f, v, "date"))
    if subject == "newborn" and any("TT" in str(x) or "Td" in str(x) for x in record.get("vaccinations_due", []) or []):
        doubts.append(Doubt("vaccinations_due", record["vaccinations_due"], "contradiction"))
    if record.get("_id_score") is not None and record["_id_score"] < 90:
        doubts.append(Doubt("beneficiary_id", record.get("beneficiary_id"), "id_match"))
    for f in record.get("_unsure", []):
        doubts.append(Doubt(f, record.get(f), "llm_unsure"))
    for f in record.get("_low_audio", []):
        if isinstance(record.get(f), (int, float)):
            doubts.append(Doubt(f, record.get(f), "low_audio"))
    return sorted(doubts, key=lambda d: PRIORITY[d.kind])


def plan(record: dict, subject: str, today: dt.date, safety_signs: list[str],
         extras: list[Doubt] = (), max_questions: int = 1) -> ReadbackPlan:
    doubts = find_doubts(record, subject, today, extras)
    question = doubts[0] if doubts and max_questions else None
    return ReadbackPlan(question, safety_signs[:3])


def after_safety_turn(asked: list[str], answered: set[str]) -> list[str]:
    """Signs she did not answer are recorded as 'unverified, ANM check', never as absent."""
    return [s for s in asked if s not in answered]
