"""Everything the agent says: fixed templates, typed slots, guard, disclosure first.

The LLM never writes sentences; it only fills slots. Numbers and dates are
verbalised before they enter a template. Kannada template wording is
UNSOURCED-linguistic and needs a native-speaker check.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache

from .danger import load_lexicon, sign_label
from .guard import guard
from .text import DATA
from . import verbalize

TEMPLATES = {
    "disclosure": {
        "hi": "Main AI hoon. Khatre ke nishaan mein jo saaf na ho, woh poochungi ya ANM ke liye nishaan "
              "laga dungi. Ilaaj ya dawa nahi bataungi. Ghar mein koi sun raha ho to 'dheere' boliye.",
        "kn": "ನಾನು AI. ಅಪಾಯದ ಲಕ್ಷಣ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲದಿದ್ದರೆ ಕೇಳುತ್ತೇನೆ ಅಥವಾ ANM ಗಾಗಿ ಗುರುತು ಹಾಕುತ್ತೇನೆ. "
              "ಚಿಕಿತ್ಸೆ ಅಥವಾ ಔಷಧಿ ಹೇಳುವುದಿಲ್ಲ.",
        "en": "I am an AI. If a danger sign is unclear I will ask, or flag it for the ANM. "
              "I will not give treatment or medicine advice.",
    },
    "alert": {
        "hi": "<slow> Yeh ek khatre ka sanket ho sakta hai: {sign}. <pauses> Kripya turant PHC refer karein.",
        "kn": "<slow> ಇದು ಅಪಾಯದ ಲಕ್ಷಣ ಇರಬಹುದು: {sign}. <pauses> ದಯವಿಟ್ಟು ತಕ್ಷಣ PHC ಗೆ ರೆಫರ್ ಮಾಡಿ.",
        "en": "<slow> This may be a danger sign: {sign}. <pauses> Please refer to the PHC now.",
    },
    "choice": {
        "hi": "Maine {heard} suna. {a} ya {b}?",
        "kn": "ನಾನು {heard} ಕೇಳಿದೆ. {a} ಅಥವಾ {b}?",
        "en": "I heard {heard}. {a} or {b}?",
    },
    "confirm_value": {
        "hi": "{field} {value}, sahi hai?",
        "kn": "{field} {value}, ಸರಿನಾ?",
        "en": "{field} {value}, is that right?",
    },
    "acknowledge": {"hi": "Theek hai.", "kn": "ಸರಿ.", "en": "Okay."},
    "confirm_short": {"hi": "Sahi hai?", "kn": "ಸರಿನಾ?", "en": "Is that right?"},
    "value_again": {
        "hi": "Sahi maap boliye.",
        "kn": "ಸರಿಯಾದ ಅಳತೆಯನ್ನು ಹೇಳಿ.",
        "en": "Please say the correct value.",
    },
    "safety_retry": {
        "hi": "Har nishaan ke liye kram se haan ya nahi boliye.",
        "kn": "ಪ್ರತಿ ಲಕ್ಷಣಕ್ಕೆ ಕ್ರಮವಾಗಿ ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.",
        "en": "Say one yes or no for each remaining sign, in order.",
    },
    "safety_turn": {
        "hi": "<pauses> Ek-ek karke bataiye, hai ya nahi: {signs}. Isi kram mein jawab dijiye.",
        "kn": "<pauses> ಒಂದೊಂದಾಗಿ ಹೇಳಿ, ಇದೆಯಾ ಇಲ್ಲವಾ: {signs}.",
        "en": "<pauses> One by one, yes or no: {signs}. Answer in that order.",
    },
    "summary": {
        "hi": "{summary}. Save karne ke liye 'record pakka' boliye.",
        "kn": "{summary}. ಉಳಿಸಲು 'record pakka' ಅನ್ನಿ.",
        "en": "{summary}. Say 'record pakka' to save.",
    },
    "saved": {
        "hi": "Record save ho gaya. Badalna ho to paanch second mein 'ruko' boliye.",
        "kn": "ರೆಕಾರ್ಡ್ ಉಳಿಸಲಾಗಿದೆ. ಬದಲಿಸಬೇಕಾದರೆ ಐದು ಸೆಕೆಂಡಿನಲ್ಲಿ 'ruko' ಅನ್ನಿ.",
        "en": "Record saved. Say 'ruko' within five seconds to undo.",
    },
    "confirm_beneficiary": {
        "hi": "Kya aap {name}, ID {id} ki baat kar rahi hain?",
        "kn": "ನೀವು {name}, ID {id} ಬಗ್ಗೆ ಹೇಳುತ್ತಿದ್ದೀರಾ?",
        "en": "Do you mean {name}, ID {id}?",
    },
    "concern_noted": {
        "hi": "Yeh baat aapke shabdon mein likh li. ANM ko dikhani ho to 'ANM ko batao' boliye.",
        "kn": "ಈ ವಿಷಯವನ್ನು ನಿಮ್ಮ ಮಾತಿನಲ್ಲೇ ಬರೆದುಕೊಂಡೆ. ANM ಗೆ ತೋರಿಸಲು 'ANM ಗೆ ತಿಳಿಸಿ' ಅನ್ನಿ.",
        "en": "I noted this in your words. Say 'tell ANM' to flag it for the ANM.",
    },
    "concern_flagged": {
        "hi": "Theek hai, yeh baat ANM ke card par jaayegi.",
        "kn": "ಸರಿ, ಈ ವಿಷಯ ANM ಕಾರ್ಡ್‌ನಲ್ಲಿ ಬರುತ್ತದೆ.",
        "en": "Okay, this goes on the ANM card.",
    },
    "concern_missing": {
        "hi": "ANM ko kaun si baat batani hai? Apne shabdon mein boliye.",
        "kn": "ANM ಗೆ ಯಾವ ವಿಷಯ ತಿಳಿಸಬೇಕು? ನಿಮ್ಮ ಮಾತಿನಲ್ಲಿ ಹೇಳಿ.",
        "en": "What should the ANM know? Say it in your words.",
    },
    "save_failed": {
        "hi": "Record save nahi hua. Dobara 'record pakka' boliye.",
        "kn": "ರೆಕಾರ್ಡ್ ಉಳಿಸಲು ಆಗಲಿಲ್ಲ. ಮತ್ತೆ 'record pakka' ಅನ್ನಿ.",
        "en": "The record was not saved. Say 'record pakka' again.",
    },
    "discreet_on": {
        "hi": "Theek hai, niji baatein zor se nahi padhungi. Khatre ke nishaan hamesha bataungi.",
        "kn": "ಸರಿ, ಖಾಸಗಿ ವಿಷಯಗಳನ್ನು ಜೋರಾಗಿ ಓದುವುದಿಲ್ಲ. ಅಪಾಯದ ಲಕ್ಷಣಗಳನ್ನು ಯಾವಾಗಲೂ ಹೇಳುತ್ತೇನೆ.",
        "en": "Okay, I will not read private details aloud. Danger signs will always be read.",
    },
    "undone": {
        "hi": "Theek hai, save radd kar diya. Jo badalna hai, boliye.",
        "kn": "ಸರಿ, ಉಳಿಸಿದ್ದನ್ನು ರದ್ದು ಮಾಡಿದೆ. ಏನು ಬದಲಿಸಬೇಕು, ಹೇಳಿ.",
        "en": "Okay, the save is undone. Tell me what to change.",
    },
    "out_of_scope": {
        "hi": "Main sirf visit record mein madad kar sakti hoon.",
        "kn": "ನಾನು ಭೇಟಿ ದಾಖಲೆಗೆ ಮಾತ್ರ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ.",
        "en": "I can only help with the visit record.",
    },
    "resume": {
        "hi": "Chaliye, visit aage badhaate hain.",
        "kn": "ಭೇಟಿಯನ್ನು ಮುಂದುವರಿಸೋಣ.",
        "en": "Let us continue the visit.",
    },
    "context_check": {
        "hi": "Yeh {suggested} ki baat lagti hai. Visit badal doon? Haan ya nahi.",
        "kn": "ಇದು {suggested} ವಿಷಯ ಅನಿಸುತ್ತದೆ. ಭೇಟಿ ಬದಲಿಸಲೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ.",
        "en": "This sounds like a {suggested} visit. Switch the visit? Yes or no.",
    },
    "context_which": {
        "hi": "Yeh kis visit ki baat hai: {options}?",
        "kn": "ಇದು ಯಾವ ಭೇಟಿಯ ವಿಷಯ: {options}?",
        "en": "Which visit is this about: {options}?",
    },
    "visit_switched": {
        "hi": "Theek hai, ab {visit} visit.",
        "kn": "ಸರಿ, ಈಗ {visit} ಭೇಟಿ.",
        "en": "OK, this is now a {visit} visit.",
    },
    "visit_kept": {
        "hi": "Theek hai, {visit} visit hi chalega.",
        "kn": "ಸರಿ, {visit} ಭೇಟಿಯೇ ಮುಂದುವರಿಯುತ್ತದೆ.",
        "en": "OK, staying on the {visit} visit.",
    },
}

VISIT_NAMES = {
    "anc": {"hi": "garbhavastha", "kn": "ಗರ್ಭಿಣಿ", "en": "pregnancy"},
    "pnc": {"hi": "prasav ke baad maa", "kn": "ಬಾಣಂತಿ", "en": "mother after delivery"},
    "hbnc": {"hi": "navjaat shishu", "kn": "ನವಜಾತ ಶಿಶು", "en": "newborn"},
    "hbyc": {"hi": "chhote bachche", "kn": "ಚಿಕ್ಕ ಮಗು", "en": "young child"},
}
OR_WORD = {"hi": " ya ", "kn": " ಅಥವಾ ", "en": " or "}

FIELD_NAMES = {
    "weight_kg": {"hi": "Wajan", "kn": "ತೂಕ", "en": "Weight"},
    "hb": {"hi": "HB", "kn": "HB", "en": "HB"},
    "bp": {"hi": "BP", "kn": "BP", "en": "BP"},
    "next_visit_date": {"hi": "Agla visit", "kn": "ಮುಂದಿನ ಭೇಟಿ", "en": "Next visit"},
    "beneficiary_id": {"hi": "ID", "kn": "ID", "en": "ID"},
}
UNITS = {"weight_kg": {"hi": "kilo", "kn": "ಕಿಲೋ", "en": "kilo"}}


@lru_cache(maxsize=None)
def spoken_sign(sign: str, lang: str) -> str:
    """Name of a danger sign in her language: the official Hindi wording where it exists."""
    if lang == "en":
        return sign_label(sign)
    entries = json.loads((DATA / "lexicon.json").read_text("utf-8"))[sign].get(lang, [])
    official = [e for e in entries if e["provenance"].startswith("OFFICIAL")]
    pick = (official or entries or [{"script": sign_label(sign)}])[0]["script"]
    return pick.split("/")[0].split("(")[0].strip()


def value_words(field: str, value, lang: str) -> str:
    if field == "bp":
        by = {"hi": "by", "kn": "ಬೈ", "en": "by"}[lang]
        return f"{verbalize.integer(int(value[0]), lang)} {by} {verbalize.integer(int(value[1]), lang)}"
    if field == "beneficiary_id":
        return verbalize.digits(str(value), lang)
    if isinstance(value, dt.date):
        return verbalize.date(value, lang)
    words = verbalize.number(value, lang)
    unit = UNITS.get(field, {}).get(lang)
    return f"{words} {unit}" if unit else words


class Speaker:
    """Renders templates. Refuses to say anything before the AI disclosure."""

    def __init__(self, lang: str = "hi"):
        self.lang = lang
        self.disclosed = False
        self.blocked: list[tuple[str, list[str]]] = []

    def say(self, key: str, **slots) -> str:
        if key != "disclosure" and not self.disclosed:
            raise RuntimeError("the first turn of every session must be the AI disclosure")
        text = TEMPLATES[key][self.lang].format(**slots)
        safe, bad = guard(text, self.lang)
        if bad:
            self.blocked.append((text, bad))
        if key == "disclosure":
            self.disclosed = True
        return safe

    def alert(self, sign: str) -> str:
        return self.say("alert", sign=spoken_sign(sign, self.lang))

    def visit_name(self, visit_type: str) -> str:
        return VISIT_NAMES[visit_type][self.lang]

    def context_question(self, suggested: list[str], current: str) -> str:
        """One other visit: "switch? yes or no". Several: "which visit: a, b or c?"."""
        if len(suggested) == 1:
            return self.say("context_check", suggested=self.visit_name(suggested[0]))
        names = [self.visit_name(v) for v in [current, *suggested]]
        return self.say("context_which", options=", ".join(names[:-1]) + OR_WORD[self.lang] + names[-1])

    def safety_turn(self, signs: list[str]) -> str:
        sep = {"hi": ", ", "kn": ", ", "en": ", "}[self.lang]
        return self.say("safety_turn", signs=sep.join(spoken_sign(s, self.lang) for s in signs))

    def choice(self, field: str, heard, a, b) -> str:
        return self.say("choice", heard=value_words(field, heard, self.lang),
                        a=value_words(field, a, self.lang), b=value_words(field, b, self.lang))

    def confirm_beneficiary(self, person: dict) -> str:
        return self.say("confirm_beneficiary", name=person["name"],
                        id=verbalize.digits(str(person["id"]), self.lang))

    def confirm(self, field: str, value) -> str:
        return self.say("confirm_value", field=FIELD_NAMES.get(field, {}).get(self.lang, field),
                        value=value_words(field, value, self.lang))
