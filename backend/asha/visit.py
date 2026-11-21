"""One home visit, turn by turn: the glue between the modules (no network, no LLM).

    visit = Visit("hbnc", subject="newborn", lang="hi")
    visit.start()                       -> disclosure (always first)
    visit.hear(transcript, "hi-IN")     -> lines to speak now (danger alerts first)
    visit.readback()                    -> one choice question and/or one safety turn, or the summary
    visit.hear("record pakka")          -> saved, with a 5-second undo

Field extraction here is rule-based (numbers and dates). In the full system an
LLM fills the other fields as a JSON patch; it never produces speech.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .correction import is_commit
from .danger import DangerChecker
from .dates import resolve
from .numbers import extract_measurements
from .readback import Doubt, plan
from .speak import Speaker

DATE_CUES = {"visit", "aana", "aaungi", "aayegi", "milenge", "barteeni", "bartini", "ಬರ್ತೀನಿ", "tareekh",
             "taareekhu", "agla", "agle", "mundina", "naale", "kal", "parson"}


@dataclass
class Visit:
    visit_type: str
    subject: str = "mother"           # whose numbers: "mother" | "newborn" | "child"
    lang: str = "hi"
    today: dt.date = field(default_factory=dt.date.today)
    tested_languages: tuple = ("hi", "en")

    def __post_init__(self):
        self.danger = DangerChecker(self.visit_type, self.tested_languages)
        self.speaker = Speaker(self.lang)
        self.record: dict = {}
        self.extra_doubts: list[Doubt] = []
        self.alerted: list[str] = []
        self.saved = False

    def start(self) -> list[str]:
        return [self.speaker.say("disclosure")]

    def hear(self, text: str, language_code: str | None = None) -> list[str]:
        language_code = language_code or f"{self.lang}-IN"
        if is_commit(text):
            self.saved = True
            return [self.speaker.say("saved")]
        out = []
        new = self.danger.add_utterance(text, language_code)
        m = extract_measurements(text, self.subject)
        for key in ("weight_kg", "hb", "bp", "temperature", "breaths_per_min"):
            if key in m:
                self.record[key] = m[key]
        for f, v, reason in m["doubts"]:
            if reason != "outside plausible range":     # range doubts are found again by readback
                self.extra_doubts.append(Doubt(f, v, "approximate"))
        new += self.danger.add_vitals(m)
        words = set(text.lower().split())
        if words & DATE_CUES:
            r = resolve(text, self.today)
            if r and r.kind == "date":
                self.record["next_visit_date"] = r.value
                if r.confirm:
                    self.extra_doubts.append(Doubt("next_visit_date", r.value, "date"))
            elif r and r.kind == "ambiguous":
                self.extra_doubts.append(Doubt("next_visit_date", None, "date"))
        for s in new:                                   # escalation is never deferred
            if s not in self.alerted:
                self.alerted.append(s)
                out.append(self.speaker.alert(s))
        return out

    def readback(self) -> list[str]:
        p = plan(self.record, self.subject, self.today, self.danger.safety_questions(),
                 extras=self.extra_doubts)
        out = []
        q = p.question
        if q and q.alternative is not None:
            out.append(self.speaker.choice(q.field, q.value, q.alternative, q.value))
        elif q and q.value is not None:
            out.append(self.speaker.confirm(q.field, q.value))
        if p.safety_signs:
            out.append(self.speaker.safety_turn(p.safety_signs))
        if not out:
            out.append(self.speaker.say("summary", summary=self._summary()))
        return out

    def _summary(self) -> str:
        parts = [self.speaker.confirm(f, v).rsplit(",", 1)[0]
                 for f, v in self.record.items() if f in ("weight_kg", "bp", "hb", "next_visit_date")]
        return "; ".join(parts) or "Koi naya maap nahi"
