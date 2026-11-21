"""One home visit, turn by turn: the glue between the modules.

    visit = Visit("hbnc", subject="newborn", lang="hi")
    visit.start()                       -> disclosure (always first)
    visit.hear(transcript, "hi-IN")     -> lines to speak now (danger alerts first)
    visit.readback()                    -> one choice question and/or one safety turn, or the summary
    visit.hear("record pakka")          -> saved, with a 5-second undo
    visit.events()                      -> browser events since the last call (record, alert, ...)

Numbers and dates come from the rules (numbers.py, dates.py). Every line returned is
already guarded and ready for TTS.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from .concern import carries_content, is_flag_request, is_worry
from . import medicines
from .context import COVERS, SUBJECTS, VISIT_TYPES, answer_to_switch, context_cues, out_of_scope
from .correction import apply_correction, is_commit, is_undo
from .danger import NOT_CHECKED, PRESENT, RULED_OUT, DangerChecker, Evidence, sign_label
from .dates import resolve
from .numbers import KILO, extract_measurements, parse_numbers
from .readback import Doubt, find_doubts, plan
from .speak import FIELD_NAMES, Speaker, spoken_sign
from .text import tokens

DATE_CUES = {"visit", "aana", "aaungi", "aayegi", "milenge", "barteeni", "bartini", "ಬರ್ತೀನಿ", "tareekh",
             "taareekhu", "agla", "agle", "mundina", "naale", "kal", "parson"}
RULE_FIELDS = ("weight_kg", "hb", "bp", "temperature", "breaths_per_min")
# LLM schema name -> record name (readback.py uses "vaccinations_*")
LLM_FIELDS = {"weight_kg": "weight_kg", "hb": "hb", "breaths_per_min": "breaths_per_min",
              "ifa_taking": "ifa_taking", "vaccines_given": "vaccinations_given",
              "vaccines_due": "vaccinations_due", "next_visit_text": "next_visit_text"}
KANNADA_MONTH_ORDINALS = {
    "ಮೊದಲ": 1, "ಎರಡನೇ": 2, "ಮೂರನೇ": 3, "ನಾಲ್ಕನೇ": 4, "ಐದನೇ": 5,
    "ಆರನೇ": 6, "ಏಳನೇ": 7, "ಎಳನೇ": 7, "ಎಲೆನೇ": 7, "ಎಲ್ನಿ": 7, "ಎಲ್ನೇ": 7, "elane": 7,
    "ಎಂಟನೇ": 8, "ಒಂಬತ್ತನೇ": 9,
}
ENGLISH_ORDINALS = {word: i for i, word in enumerate(
    ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"), 1
)}
MEASUREMENT_PROMPTS = {"bp": "bp_both_values", "temperature": "temperature_repeat",
                       "gestational_trimester": "trimester_repeat"}
DISCREET_WORDS = {"dheere", "dhire", "dheere-dheere", "धीरे", "ಮೆಲ್ಲಗೆ", "quietly"}
DISCREET_MAX_WORDS = 3                # longer sentences with "dheere" are content, not a command
# Never read aloud in discreet mode (the screen still shows them). Danger signs are always read.
SENSITIVE_FIELDS = {"family_planning", "contraception", "pregnancy_loss", "abortion",
                    "miscarriage", "stillbirth"}
LLM_WAIT_S = 15.0                    # upper bound; llm.py's own timeouts are 3 s + 8 s

# Narrow answer vocabulary: "okay" may acknowledge the question without asserting a symptom.
YES_ANSWERS = {"yes", "haan", "han", "ha", "हाँ", "हां", "हा", "ಹೌದು", "howdu", "haudu"}
NO_ANSWERS = {"no", "nahi", "nahin", "नहीं", "नही", "illa", "ಇಲ್ಲ"}
SKIP_ANSWERS = {("not", "sure"), ("skip",), ("pata", "nahi"), ("पता", "नहीं"), ("ಗೊತ್ತಿಲ್ಲ",)}
ANSWER_FILLERS = {"ji", "जी", "hai", "है", "hain", "हैं", "please"}

log = logging.getLogger("asha.visit")
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def jsonable(v):
    """Record values -> JSON for the browser: dates as ISO strings, tuples as lists."""
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, tuple):
        return [jsonable(x) for x in v]
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    return v


@dataclass
class Visit:
    visit_type: str
    subject: str = "mother"           # whose numbers: "mother" | "newborn" | "child"
    lang: str = "hi"
    today: dt.date = field(default_factory=dt.date.today)
    tested_languages: tuple = ("hi", "en")
    use_llm: bool = True              # False: rules only (tests, text demo)
    understand: Callable[[str, str, dict], dict] | None = None   # default: llm.understand
    clock: Callable[[], float] = time.monotonic                  # for the 5-second undo
    beneficiary_id: str = ""
    use_store: bool = True            # False: nothing written to disk (tests, text demo)
    report_session: str | None = None
    store: Any = None                 # default: store.default_store() (encrypted SQLite)

    def __post_init__(self):
        self.danger = DangerChecker(self.visit_type, self.tested_languages)
        self.speaker = Speaker(self.lang)
        self.record: dict = {}
        self.evidence: dict[str, str] = {}      # field -> her words
        self.extra_doubts: list[Doubt] = []
        self.alerted: list[str] = []
        self.saved = False
        self.saved_at: float | None = None
        self.discreet = False
        self._events: list[dict] = []
        self._unspoken: list[str] = []          # lines found after hear() returned (LLM alerts)
        self._pending: list[tuple[Future, str, int, set[str]]] = []
        self.transcript: list[dict] = []        # everything she said, with time (saved encrypted)
        self.flags: list[dict] = []             # every danger flag: sign, quote, time, rules or llm
        self.visit_id: int | None = None
        self._heard: list[tuple[str, str]] = []  # every sentence the checker saw, to replay on a switch
        self._switch_offer: list[str] | None = None   # visit types we just asked her about
        self._asked_context: set[str] = set()   # never ask about the same other visit twice
        self._replied: set[int] = set()         # utterances already given an out-of-scope / context reply
        self._readback_done = False
        self._measurement_repeats: set[str] = set()
        self._pending_doubt: Doubt | None = None
        self._safety_pending: list[str] = []
        self._safety_disagreements: list[str] = []
        self._safety_started = False
        self._checklist_snapshot = None
        self.switches: list[dict] = []          # every visit-type change: from, to, time, by
        if self.use_store and self.store is None:
            from store import default_store     # lazy: rules-only visits never touch the disk
            self.store = default_store()
        if self.use_llm and self.understand is None:
            from llm import understand          # lazy: rules-only visits never touch the network
            self.understand = understand

    # ---------- contract with app.py ----------

    def start(self) -> list[str]:
        return [self.speaker.say("disclosure")]

    def resume(self) -> list[str]:
        """Repeat the current prompt after the voice connection was interrupted."""
        lines = self.readback()
        if self.saved:
            return lines
        if self._switch_offer:
            prompt = self.speaker.context_question(self._switch_offer, self.visit_type)
        elif self._pending_doubt:
            doubt = self._pending_doubt
            if doubt.alternative is not None:
                prompt = self.speaker.choice(doubt.field, doubt.value, doubt.alternative, doubt.value)
            else:
                prompt = self.speaker.confirm(doubt.field, doubt.value)
        elif self._measurement_repeats:
            prompt = self._measurement_prompt()
        elif self._safety_started:
            prompt = (self._spoken_safety_question(self._safety_pending[0]) if self._safety_pending
                      else self.speaker.say("summary", summary=self._summary()))
        else:
            return lines
        return lines if prompt in lines else lines + self._question(prompt)

    def hear(self, text: str, language_code: str | None = None) -> list[str]:
        language_code = language_code or f"{self.lang}-IN"
        self.transcript.append({"at": now(), "text": text, "lang": language_code})
        if self.saved:
            if is_undo(text, self.clock() - self.saved_at):
                self.saved, self.saved_at = False, None
                if self.store and self.visit_id is not None:
                    self.store.mark_undone(self.visit_id, now())
                self.visit_id = None
                self._events.append({"type": "undo"})
                return [self.speaker.say("undone")]
            log.info("visit already saved; ignoring: %r", text)
            return []
        if is_commit(text):
            return self.confirm()
        words = [t.text for t in tokens(text)]
        if len(words) <= DISCREET_MAX_WORDS and set(words) & DISCREET_WORDS:
            self.discreet = True
            self._events.append({"type": "discreet", "on": True})
            return self._take_unspoken() + [self.speaker.say("discreet_on")]
        flag = is_flag_request(words)
        if flag and not carries_content(words):     # "ANM ko batao": flag the concern she just said
            return self._take_unspoken() + [self._flag_last_concern()]
        if self._switch_offer is not None:      # her answer to "switch the visit?"
            reply = self._answer_switch(words)
            if reply is not None:
                return self._take_unspoken() + reply
        if self._pending_doubt is not None:
            reply = self._answer_doubt(text, words)
            if reply is not None:
                return self._take_unspoken() + reply
        if self._readback_done and self._measurement_repeats and tuple(words) in SKIP_ANSWERS:
            self._measurement_repeats.remove(self._next_measurement())
            if self._measurement_repeats:
                return self._take_unspoken() + self._question(self._measurement_prompt())
            return self._take_unspoken() + self._start_safety()
        if self._safety_pending:
            reply = self._answer_safety(text, words)
            if reply is not None:
                return self._take_unspoken() + reply
        return self._hear_content(text, language_code, words, flag)

    def add_note(self, text: str, language_code: str) -> list[str]:
        """Process a typed or imported note without treating it as a voice command."""
        self.transcript.append({"at": now(), "text": text, "lang": language_code})
        return self._hear_content(text, language_code, [t.text for t in tokens(text)], False)

    def confirm(self) -> list[str]:
        self._drain(wait=True)
        return self._take_unspoken() + self._save()

    def answer_checklist(self, sign: str, answer: str) -> list[str]:
        """Apply an explicit answer linked to the question displayed on the phone."""
        idx = len(self.danger.utterances)
        text = f"{spoken_sign(sign, self.lang)}: {answer}"
        self.danger.utterances.append(text)
        self.transcript.append({"at": now(), "text": text, "lang": f"{self.lang}-IN"})
        pending = bool(self._safety_pending and self._safety_pending[0] == sign)
        if sign in self._safety_pending:
            self._safety_pending.remove(sign)
        lines = []
        if answer == "yes":
            if self.danger.add_external(sign, text, idx, phrase="safety_answer"):
                lines = self._alerts([sign])
        else:
            status = RULED_OUT if answer == "no" else NOT_CHECKED
            self.danger.states[sign].evidence.append(Evidence(status, text, idx, phrase="safety_answer"))
        if pending:
            lines += self._continue_safety()
        return lines

    def _hear_content(self, text, language_code, words, flag):
        self._drain(wait=False)
        llm_job = None
        if self.use_llm:                        # start first so it runs while the rules work
            llm_job = _POOL.submit(self.understand, text, self.visit_type, jsonable(
                {k: v for k, v in self.record.items() if k != "worker_concerns"}))   # not LLM input
        self._heard.append((text, language_code))
        new = self.danger.add_utterance(text, language_code)
        idx = len(self.danger.utterances) - 1
        m = extract_measurements(text, self.subject)
        if "bp" in self._measurement_repeats and "bp" not in m:
            values = parse_numbers(text)
            if (len(values) == 2 and values[0].start == 0 and values[1].end == len(words) - 1
                    and values[1].start == values[0].end + 1):
                m = extract_measurements("BP " + text, self.subject)
        changed = False
        previous_repeats = self._measurement_repeats.copy()
        if self.visit_type == "anc":
            for i, (ordinal, unit) in enumerate(zip(words, words[1:])):
                digits = ordinal.removesuffix("st").removesuffix("nd").removesuffix("rd").removesuffix("th")
                stage = ENGLISH_ORDINALS.get(ordinal) or (int(digits) if len(digits) <= 2 and digits.isdecimal() else None)
                if (stage is not None and i >= 2 and words[i - 2:i] == ["in", "her"]
                        and words[i + 1:i + 3] == ["prime", "minister"]):
                    # Observed recognition error in a pregnancy-stage phrase. Ask her to repeat.
                    self._measurement_repeats.add("gestational_trimester")
                elif unit == "trimester" and stage is not None:
                    if stage in (1, 2, 3):
                        self._set("gestational_trimester", stage, text)
                        self._measurement_repeats.discard("gestational_trimester")
                        changed = True
                    else:
                        self._measurement_repeats.add("gestational_trimester")
                if unit == "month" and stage in range(1, 10) and (ordinal in ENGLISH_ORDINALS or ordinal != digits):
                    self._set("gestational_month", stage, text)
                    changed = True
                if unit in {"ತಿಂಗಳು", "tingalu"} and ordinal in KANNADA_MONTH_ORDINALS:
                    self._set("gestational_month", KANNADA_MONTH_ORDINALS[ordinal], text)
                    changed = True
        invalid = {f for f, _, reason in m["doubts"]
                   if f in ("bp", "temperature") and reason == "outside plausible range"}
        self._measurement_repeats.difference_update(({"bp", "temperature"} & m.keys()) - invalid)
        self._measurement_repeats.update(invalid)
        if "bp_partial" in m and "bp" not in m:
            self._measurement_repeats.add("bp")
        for key in RULE_FIELDS:
            if key in m and key not in invalid:
                self._set(key, m[key], text)
                changed = True
        if self._note_medicines(text, words):
            changed = True
        if llm_job:
            rule_fields = {k for k in RULE_FIELDS if k in m}
            if "bp_partial" in m:
                rule_fields.add("bp")
            self._pending.append((llm_job, text, idx, rule_fields))
        for f, v, reason in m["doubts"]:
            if reason != "outside plausible range":     # range doubts are found again by readback
                self.extra_doubts.append(Doubt(f, v, "approximate"))
        new += self.danger.add_vitals(m)
        if set(text.lower().split()) & DATE_CUES:
            r = resolve(text, self.today)
            if r and r.kind == "date":
                self._set("next_visit_date", r.value, text)
                changed = True
                if r.confirm:
                    self.extra_doubts.append(Doubt("next_visit_date", r.value, "date"))
            elif r and r.kind == "ambiguous":
                self.extra_doubts.append(Doubt("next_visit_date", None, "date"))
        if changed:
            self._emit_record()
        alerts = self._alerts(new)                           # rule alerts first, never deferred
        concern = self._add_concern(text, flag) if flag or is_worry(words) else []
        if out_of_scope(words):                 # medicine / dose / diagnosis: never answered
            steer = self._scope_reply(idx)
        else:
            steer = self._context_reply(words, text, language_code, idx)
        checked = [sign for sign in self._safety_pending
                   if any(e.utterance == idx for e in self.danger.states[sign].evidence)]
        if checked:
            self._safety_pending = [sign for sign in self._safety_pending if sign not in checked]
            steer += self._continue_safety()
        if self._safety_started:
            for sign in self.danger.uncertain_signs.get(idx, ()):
                if sign not in self._safety_pending and self.danger.states[sign].status == NOT_CHECKED:
                    if self._safety_pending:
                        self._safety_pending.insert(1, sign)
                    else:
                        self._safety_pending.append(sign)
                        steer += self._continue_safety()
        if (self._readback_done and not self._pending_doubt
                and (previous_repeats != self._measurement_repeats
                     or (self._measurement_repeats and ("bp_partial" in m or invalid)))):
            if self._measurement_repeats:
                steer += self._question(self._measurement_prompt())
            else:
                steer += self._start_safety()
        return alerts + concern + steer + self._take_unspoken()

    def followup(self) -> list[str]:
        """Wait for the LLM's reading of the last sentences; return anything new to speak
        (an alert only the LLM caught, or the out-of-scope line). Call after speaking hear()."""
        self._drain(wait=True)
        return self._take_unspoken()

    def readback(self) -> list[str]:
        self._drain(wait=False)
        out = self._take_unspoken()
        if self._readback_done or self.saved:
            return out
        self._readback_done = True
        if self._measurement_repeats:
            return out + self._question(self._measurement_prompt())
        doubts = [d for d in find_doubts(self.record, self.subject, self.today, self.extra_doubts)
                  if d.field in FIELD_NAMES and not (self.discreet and d.field in SENSITIVE_FIELDS)]
        question = plan({}, self.subject, self.today, [], extras=doubts).question
        if question is not None and question.value is not None:
            self._pending_doubt = question
            if question.alternative is not None:
                line = self.speaker.choice(question.field, question.value, question.alternative, question.value)
            else:
                line = self.speaker.confirm(question.field, question.value)
            return out + self._question(line)
        return out + self._start_safety()

    def _question(self, line: str) -> list[str]:
        self._events.append({"type": "question", "text": line})
        return [line]

    def _measurement_prompt(self) -> str:
        return self.speaker.say(MEASUREMENT_PROMPTS[self._next_measurement()])

    def _next_measurement(self) -> str:
        return next(field for field in MEASUREMENT_PROMPTS if field in self._measurement_repeats)

    def _start_safety(self) -> list[str]:
        if not self._safety_started:
            self._safety_started = True
            # Follow the same core questions the phone showed before recording.
            preview = self.danger.guided_questions()
            disagreements = [sign for sign in self._safety_disagreements
                             if self.danger.states[sign].status != PRESENT]
            disagreements += [sign for sign in self.danger.to_ask
                              if sign not in disagreements and self.danger.states[sign].status == NOT_CHECKED]
            self._safety_pending = disagreements + [
                sign for sign in preview if sign not in disagreements
                and ((self.danger.states[sign].status == NOT_CHECKED
                      and not any(e.phrase == "safety_answer" for e in self.danger.states[sign].evidence))
                     or self.danger.states[sign].needs_confirmation)
            ]
        return self._continue_safety()

    def _spoken_safety_question(self, sign: str) -> str:
        guided = self.danger.guided_questions()
        return self.speaker.safety_question(sign, guided.index(sign) + 1 if sign in guided else None)

    def _continue_safety(self) -> list[str]:
        line = (self._spoken_safety_question(self._safety_pending[0]) if self._safety_pending
                else self.speaker.say("summary", summary=self._summary()))
        return self._question(line)

    def _answer_doubt(self, text: str, words: list[str]) -> list[str] | None:
        doubt = self._pending_doubt
        answer = [word for word in words if word not in ANSWER_FILLERS]
        if len(answer) == 1 and answer[0] in YES_ANSWERS | NO_ANSWERS:
            if doubt.alternative is not None or answer[0] in NO_ANSWERS:
                return self._question(self.speaker.say("value_again"))
            value = doubt.value
        else:
            numbers = parse_numbers(text)
            if not isinstance(doubt.value, (int, float)) or len(numbers) != 1:
                return None
            number = numbers[0]
            rest = words[:number.start] + words[number.end + 1:]
            if set(rest) - KILO - ANSWER_FILLERS - YES_ANSWERS - NO_ANSWERS:
                return None
            value = number.value

        self._pending_doubt = None
        self.extra_doubts = [item for item in self.extra_doubts if item.field != doubt.field]
        self._set(doubt.field, value, text)
        self._emit_record()
        alerts = self._alerts(self.danger.add_vitals({doubt.field: value}))
        if self._measurement_repeats:
            return alerts + self._question(self._measurement_prompt())
        return alerts + self._start_safety()

    def _answer_safety(self, text: str, words: list[str]) -> list[str] | None:
        if tuple(words) in SKIP_ANSWERS:
            sign = self._safety_pending.pop(0)
            idx = len(self.danger.utterances)
            self.danger.utterances.append(text)
            self.danger.states[sign].evidence.append(Evidence(NOT_CHECKED, text, idx, phrase="safety_answer"))
            return self._continue_safety()
        answers = [word for word in words if word not in ANSWER_FILLERS | {"also", "bhi", "भी"}]
        if len(answers) == 1 and answers[0] in {"yesn", "yesno", "noyes"}:
            return self._question(self.speaker.say("safety_retry"))
        if not answers or set(answers) - YES_ANSWERS - NO_ANSWERS:
            return None
        if len(answers) != 1:
            return self._question(self.speaker.say("safety_retry"))

        # Assign only explicit answers, in the exact order of the last question.
        idx = len(self.danger.utterances)
        self.danger.utterances.append(text)
        newly = []
        for sign, answer in zip(self._safety_pending, answers):
            if answer in YES_ANSWERS:
                if self.danger.add_external(sign, text, idx, phrase="safety_answer"):
                    newly.append(sign)
            else:
                self.danger.states[sign].evidence.append(Evidence(RULED_OUT, text, idx, phrase="safety_answer"))
        del self._safety_pending[:len(answers)]
        return self._alerts(newly) + self._continue_safety()

    def events(self) -> list[dict]:
        """Browser events since the last call; the queue is cleared."""
        self._drain(wait=False)                 # finished LLM results reach the screen early
        if self.report_session and not self.saved:
            rows = self.checklist_rows()
            if rows != self._checklist_snapshot:
                self._checklist_snapshot = rows
                self._events.append({"type": "receipt", "rows": rows})
        out, self._events = self._events, []
        return out

    # ---------- LLM merge ----------

    def _drain(self, wait: bool) -> None:
        still = []
        for job, text, idx, rule_fields in self._pending:
            if not wait and not job.done():
                still.append((job, text, idx, rule_fields))
                continue
            try:
                result = job.result(timeout=LLM_WAIT_S)
            except Exception as e:              # llm.understand catches its own errors; this is a backstop
                log.warning("llm job failed: %s: %s", type(e).__name__, e)
                continue
            self._merge(result, text, idx, rule_fields)
        self._pending = still

    def _merge(self, result: dict, text: str, idx: int, rule_fields: set[str]) -> None:
        """Rules win for numbers and dates; the LLM only fills what is still empty, except for
        fields she explicitly corrects. Either checker can flag a danger sign."""
        if not result.get("ok"):
            return
        llm_fields, quotes = result.get("fields", {}), result.get("evidence", {})
        patch, words = {}, {}
        for name, value in llm_fields.items():
            if name in LLM_FIELDS:
                patch[LLM_FIELDS[name]], words[LLM_FIELDS[name]] = value, quotes.get(name, text)
        if "bp_systolic" in llm_fields and "bp_diastolic" in llm_fields:
            patch["bp"] = (llm_fields["bp_systolic"], llm_fields["bp_diastolic"])
            words["bp"] = quotes.get("bp_systolic", text)
        if "temperature" in llm_fields:
            t = llm_fields["temperature"]
            patch["temperature"], words["temperature"] = (t["value"], t["unit"]), quotes.get("temperature", text)
        named = {LLM_FIELDS.get(f, f) for f in result.get("correction_of", [])}
        if {"bp_systolic", "bp_diastolic"} & set(result.get("correction_of", [])):
            named.add("bp")
        patch = {k: v for k, v in patch.items() if k not in rule_fields}      # rules win
        fill = {k: v for k, v in patch.items() if k not in self.record}
        fixed = apply_correction(self.record, patch, named).applied
        changed = {**fill, **fixed}
        for k, v in changed.items():
            self._set(k, v, words[k])
        for f in result.get("unsure", []):              # unclear words: doubt the value, whoever set it
            f = "bp" if f in ("bp_systolic", "bp_diastolic") else LLM_FIELDS.get(f, f)
            if f in self.record and not any(d.field == f for d in self.extra_doubts):
                self.extra_doubts.append(Doubt(f, self.record[f], "llm_unsure"))

        new = self.danger.add_vitals({k: v for k, v in changed.items()
                                      if k in ("bp", "temperature", "breaths_per_min", "weight_kg")})
        general_denial = tuple(t.text for t in tokens(text)) in {
            ("abhi", "bimar", "nahi", "hai"), ("abhi", "beemar", "nahi", "hai"),
            ("koi", "dikkat", "nahi"), ("koi", "dikkat", "nahi", "hai"),
            ("sab", "theek", "hai"), ("अभी", "बीमार", "नहीं", "है"),
            ("कोई", "दिक्कत", "नहीं", "है"), ("सब", "ठीक", "है"),
        }
        for s in result.get("danger_signs", []):
            sign = s["id"]
            state = self.danger.states.get(sign)
            if state is None or s["status"] not in ("present", "past"):
                continue
            denied = sign in self.danger.denied_signs.get(idx, ())
            uncertain = sign in self.danger.uncertain_signs.get(idx, ())
            if uncertain:
                continue
            if general_denial or denied:
                if state.status != PRESENT and sign not in self._safety_disagreements:
                    self._safety_disagreements.append(sign)
                    if self._safety_started and sign not in self._safety_pending:
                        if self._safety_pending:
                            # Keep the question she already heard at the front.
                            self._safety_pending.insert(1, sign)
                        else:
                            self._safety_pending.append(sign)
                            self._unspoken += self._continue_safety()
                continue
            if self.danger.add_external(sign, s.get("evidence") or text, idx,
                                        history=s["status"] == "past"):
                new.append(sign)
        if changed:
            self._emit_record()
        self._unspoken += self._alerts(new)
        other = result.get("visit_context")
        if idx in self._replied:                # the rules already answered this sentence
            return
        if other and self._other_visit(other) and other not in self._asked_context:
            self._unspoken += self._offer_switch([other], idx)
        elif result.get("off_topic"):
            self._unspoken += self._scope_reply(idx)

    def _take_unspoken(self) -> list[str]:
        out, self._unspoken = self._unspoken, []
        return out

    # ---------- out of scope and visit context ----------

    def set_visit_type(self, visit_type: str, by: str = "screen") -> list[str]:
        """Switch to another visit's checklist (her spoken yes, or the dropdown on the screen).
        Everything she said is checked again against the new checklist. Signs already flagged stay
        flagged: their alerts were spoken, they stay in the audit trail, and any sign the new
        checklist does not have is kept in the record as "flags_before_switch" for the ANM."""
        if visit_type not in VISIT_TYPES:
            raise ValueError(f"unknown visit type {visit_type!r}")
        self._switch_offer = None
        if self.saved:
            return []
        if visit_type == self.visit_type:
            return [self.speaker.say("visit_kept", visit=self.speaker.visit_name(visit_type))]
        old = self.danger
        self._safety_pending.clear()
        self._safety_disagreements.clear()
        self._pending_doubt = None
        self.switches.append({"from": self.visit_type, "to": visit_type, "at": now(), "by": by})
        self.visit_type, self.subject = visit_type, SUBJECTS[visit_type]
        self.danger = DangerChecker(visit_type, self.tested_languages)
        for text, code in self._heard:
            self.danger.add_utterance(text, code)
        for sign, state in old.states.items():  # what the LLM flagged carries over where it applies
            for e in state.evidence:
                if e.status == PRESENT and e.phrase in {"llm", "safety_answer"}:
                    self.danger.add_external(sign, e.quote, e.utterance, history=e.history)
        self.danger.add_vitals({k: v for k, v in self.record.items()
                                if k in ("bp", "temperature", "breaths_per_min", "weight_kg")})
        kept = [k for k in self.record.get("flags_before_switch", [])
                if k["sign"] not in self.danger.states]     # back on its own checklist: not "before" any more
        self.record["flags_before_switch"] = kept
        for sign in old.present():
            if sign not in self.danger.states and all(k["sign"] != sign for k in kept):
                kept.append({"sign": sign, "label": sign_label(sign), "visit_type": old.visit_type,
                             "quote": old.states[sign].evidence[-1].quote})
        if not kept:
            del self.record["flags_before_switch"]
        self._events.append({"type": "visit_type", "visit_type": visit_type, "subject": self.subject})
        self._emit_record()
        line = self.speaker.say("visit_switched", visit=self.speaker.visit_name(visit_type))
        return [line] + self._alerts(self.danger.present())

    def _other_visit(self, visit_type: str) -> bool:
        return (visit_type in VISIT_TYPES and visit_type != self.visit_type
                and visit_type not in COVERS.get(self.visit_type, set()))

    def _resume(self) -> str:
        """Back to the checklist: the next safety questions once the first readback has asked them."""
        signs = self._safety_pending
        return self._spoken_safety_question(signs[0]) if signs else self.speaker.say("resume")

    def _scope_reply(self, idx: int) -> list[str]:
        self._replied.add(idx)
        lines = [self.speaker.say("out_of_scope"), self._resume()]
        self._events.append({"type": "question", "text": lines[-1]})
        return lines

    def _context_reply(self, words: list[str], text: str, code: str, idx: int) -> list[str]:
        if self._switch_offer is not None:
            return []
        here = any(e.utterance == idx for st in self.danger.states.values() for e in st.evidence)
        other = sorted(context_cues(words, text, self.visit_type, here, code) - self._asked_context)
        return self._offer_switch(other, idx) if other else []

    def _offer_switch(self, suggested: list[str], idx: int) -> list[str]:
        self._replied.add(idx)
        self._switch_offer = suggested
        self._asked_context |= set(suggested)
        line = self.speaker.context_question(suggested, self.visit_type)
        self._events.append({"type": "visit_context", "current": self.visit_type, "suggested": suggested})
        self._events.append({"type": "question", "text": line})
        return [line]

    def _answer_switch(self, words: list[str]) -> list[str] | None:
        """None: not an answer, so the sentence is visit content (the question lapses)."""
        offer, answer = self._switch_offer, answer_to_switch(words)
        if answer is None:
            self._switch_offer = None
            return None
        if answer == "yes" and len(offer) > 1:  # "haan" to "which visit?": ask again
            return [self.speaker.context_question(offer, self.visit_type)]
        if answer == "no":
            self._switch_offer = None
            return [self.speaker.say("visit_kept", visit=self.speaker.visit_name(self.visit_type)),
                    self._resume()]
        return self.set_visit_type(offer[0] if answer == "yes" else answer, by="voice")

    # ---------- internals ----------

    # ---------- worker concerns (outside the checklist; never change a checklist state) ----------

    def _add_concern(self, text: str, flagged: bool) -> list[str]:
        self.record.setdefault("worker_concerns", []).append(
            {"quote": text, "at": now(), "flagged": flagged})      # her words, verbatim
        self._emit_record()
        return [self.speaker.say("concern_flagged" if flagged else "concern_noted")]

    def _flag_last_concern(self) -> str:
        concerns = self.record.get("worker_concerns", [])
        if not concerns:
            return self.speaker.say("concern_missing")
        target = next((c for c in reversed(concerns) if not c["flagged"]), concerns[-1])
        target["flagged"] = True
        self._emit_record()
        return self.speaker.say("concern_flagged")

    def _note_medicines(self, text: str, words: list[str]) -> bool:
        """Record medicines she says were already given (by another ASHA, the ANM or the PHC).
        Shown on screen and saved; never spoken."""
        if out_of_scope(words):
            return False
        found, denied = medicines.read(text)
        current = self.record.get("medicines_given", [])
        updated = medicines.merge(current, found, denied)
        if updated == current:
            return False
        if updated:
            self._set("medicines_given", updated, text)
        else:
            self.record.pop("medicines_given", None)
            self.evidence.pop("medicines_given", None)
        return True

    def _set(self, key: str, value, words: str) -> None:
        if key in self.record and self.record[key] != value:     # a new reading replaces old doubts
            self.extra_doubts = [d for d in self.extra_doubts if d.field != key]
        self.record[key] = value
        self.evidence[key] = words

    def _alerts(self, signs: list[str]) -> list[str]:
        """Speak and show each newly present sign once. Escalation is never deferred."""
        out = []
        for s in signs:
            if s in self.alerted:
                continue
            self.alerted.append(s)
            out.append(self.speaker.alert(s))
            event = self._alert_event(s)
            self._events.append(event)
            last = self.danger.states[s].evidence[-1]
            self.flags.append({"sign": s, "quote": event["quote"], "at": now(),
                               "by": "llm" if last.phrase == "llm" else "rules"})
        return out

    def _alert_event(self, sign: str) -> dict:
        meta = self.danger.lex.signs[sign]
        quote = next((e.quote for e in reversed(self.danger.states[sign].evidence)
                      if e.status == "present"), "")
        return {"type": "alert", "sign": sign, "label": sign_label(sign),
                "local": spoken_sign(sign, self.lang), "quote": quote,
                "source": meta.get("source"), "page": meta.get("page")}

    def _emit_record(self) -> None:
        self._events.append({"type": "record", "fields": jsonable(self.record),
                             "evidence": dict(self.evidence)})

    def checklist_rows(self):
        return [{**row, "label": sign_label(row["sign"]), "local": spoken_sign(row["sign"], self.lang)}
                for row in self.danger.receipt()]

    def _save(self) -> list[str]:
        if self.use_store and self.store is None:
            return [self.speaker.say("save_failed")]
        rows = self.checklist_rows()
        if self.store:
            try:
                self.visit_id = self.store.save_visit(
                    beneficiary_id=self.beneficiary_id, visit_type=self.visit_type, lang=self.lang,
                    saved_at=now(), record=jsonable(self.record), transcript=self.transcript,
                    receipt=rows, flags=self.flags, concerns=self.record.get("worker_concerns", []),
                    switches=self.switches, session_key=self.report_session)
            except Exception:                   # never claim "saved" when the disk write failed
                log.exception("saving the visit failed")
                return [self.speaker.say("save_failed")]
        self.saved, self.saved_at = True, self.clock()
        self._emit_record()
        self._events.append({"type": "receipt", "rows": rows})
        self._events.append({"type": "saved"})
        return [self.speaker.say("saved")]

    def _summary(self) -> str:
        spoken = ("weight_kg", "bp", "hb", "next_visit_date")     # never a SENSITIVE_FIELDS entry
        parts = [self.speaker.confirm(f, v).rsplit(",", 1)[0]
                 for f, v in self.record.items() if f in spoken]
        return "; ".join(parts) or "Koi naya maap nahi"
