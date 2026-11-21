"""Field-level voice correction (PLAN F6) and the commit rule.

- A correction may only change the fields she named. Anything else in the
  LLM's patch is rejected, so one "nahi, weight 2.8" can never rewrite the form.
- Danger signs are locked: a correction can never clear a present sign. If she
  disputes one, it stays present and is marked for the ANM.
- Saving needs the explicit phrase "record pakka" (a bare "haan" is too easy to
  hear by mistake), followed by a spoken echo and a 5-second undo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .text import fold, tokens

COMMIT_PHRASES = [("record", "pakka"), ("record", "save"), ("ರೆಕಾರ್ಡ್", "ಪಕ್ಕಾ"), ("रिकॉर्ड", "पक्का")]
UNDO_WORDS = {"ruko", "rukiye", "undo", "cancel", "ruk", "ರುಕೋ", "ನಿಲ್ಲಿ", "रुको"}
UNDO_SECONDS = 5.0


@dataclass
class CorrectionResult:
    record: dict
    applied: dict = field(default_factory=dict)
    rejected: dict = field(default_factory=dict)
    disputed_signs: list[str] = field(default_factory=list)


def apply_correction(record: dict, patch: dict, named_fields: set[str],
                     present_signs: set[str] = frozenset()) -> CorrectionResult:
    """Apply only the named fields. `patch` may contain "clear_signs": [...] from the LLM."""
    new = dict(record)
    result = CorrectionResult(new)
    for f, v in patch.items():
        if f == "clear_signs":
            for s in v:
                if s in present_signs:
                    result.disputed_signs.append(s)   # stays present; ANM decides
            continue
        if f in named_fields:
            new[f] = v
            result.applied[f] = v
        else:
            result.rejected[f] = v
    return result


def is_commit(text: str) -> bool:
    words = [fold(t.text) for t in tokens(text)]
    return any(all(fold(p) in words for p in phrase) for phrase in COMMIT_PHRASES)


def is_undo(text: str, seconds_since_save: float) -> bool:
    return seconds_since_save <= UNDO_SECONDS and any(t.text in UNDO_WORDS for t in tokens(text))
