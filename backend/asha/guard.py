"""Last check before anything reaches Timbre: no diagnosis, no medicine, no dose.

The Responsible AI rules zero the 10 points on any live violation, so this is a
deny-list on the final text. Speech comes from templates (speak.py), so the
guard should never fire in normal use; when it does, the text is replaced by
the fixed referral sentence and the event is logged.

Several official ASHA modules pair a danger sign with a treatment
(paracetamol, amoxicillin, cotrimoxazole, gentian violet...). Those names are
blocked here even though they appear in the cited sources.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger("asha.guard")

DRUGS = [
    "paracetamol", "crocin", "dolo", "calpol", "ibuprofen", "aspirin", "amoxicillin", "amoxycillin",
    "gentamicin", "cotrimoxazole", "septran", "metronidazole", "ciprofloxacin", "azithromycin",
    "tetracycline", "gentian violet", "misoprostol", "oxytocin", "magnesium sulphate", "mgso4",
    "antibiotic", "chloroquine", "artesunate", "albendazole", "zinc", "ors pila", "पैरासिटामोल",
    "एंटीबायोटिक", "ಪ್ಯಾರಾಸಿಟಮಾಲ್", "ಆಂಟಿಬಯಾಟಿಕ್",
]
DOSE_PATTERNS = [
    r"\b\d+(\.\d+)?\s*(mg|mcg|ml|iu|units?)\b", r"\bmilligram", r"\b(do|teen|char|ek)\s+baar\b",
    r"\bdin\s+mein\s+\w+\s+baar\b", r"\b(twice|thrice)\b", r"\bevery\s+\d+\s+hours?\b",
    r"दिन में .* बार", r"\bdose\b", r"\bखुराक\b", r"ದಿನಕ್ಕೆ\s+\S+\s+ಬಾರಿ", r"\bdosage\b",
]
TREATMENT_VERBS = [
    r"\bgoli\s+(khaiye|khao|khilaiye|do|dijiye)\b", r"\b(khilaiye|pilaiye|lagaiye)\b", r"\bdawa(i)?\s+(do|dijiye|lijiye|lo)\b",
    r"गोली (खाइए|खाओ|खिलाइए|दीजिए)", r"दवा (दीजिए|लीजिए|दो)", r"\b(take|give)\s+(the\s+)?(tablet|medicine|syrup)",
    r"ಮಾತ್ರೆ\s+(ಕೊಡಿ|ತಗೊಳ್ಳಿ|ನುಂಗಿ)", r"ಔಷಧಿ\s+(ಕೊಡಿ|ತಗೊಳ್ಳಿ)",
]
DIAGNOSIS = [
    r"\b(pneumonia|sepsis|eclampsia|pre-?eclampsia|malaria|typhoid|tuberculosis|meningitis|tetanus)\b",
    r"\b(diagnos\w*|you have|she has|baby has)\b", r"\b(bimari|beemari|rog)\s+hai\b",
    r"(बीमारी|रोग) है", r"ರೋಗ\s+ಇದೆ", r"\binfection\s+hai\b",
]

FALLBACK = {
    "hi": "Main ilaaj ya dawa nahi bata sakti. Kripya ANM ya PHC se baat karein.",
    "kn": "ನಾನು ಚಿಕಿತ್ಸೆ ಅಥವಾ ಔಷಧಿ ಹೇಳುವುದಿಲ್ಲ. ದಯವಿಟ್ಟು ANM ಅಥವಾ PHC ಅವರನ್ನು ಸಂಪರ್ಕಿಸಿ.",
    "en": "I can't advise on treatment or medicine. Please speak to the ANM or the PHC.",
}

_compiled = [re.compile(p, re.I) for p in DOSE_PATTERNS + TREATMENT_VERBS + DIAGNOSIS]


def violations(text: str) -> list[str]:
    low = text.lower()
    found = [d for d in DRUGS if d in low]
    found += [p.pattern for p in _compiled if p.search(text)]
    return found


def guard(text: str, lang: str = "hi") -> tuple[str, list[str]]:
    """Returns (safe text, violations). Blocked text is replaced, never edited."""
    bad = violations(text)
    if bad:
        log.warning("guard blocked output: %s", bad)
        return FALLBACK.get(lang, FALLBACK["hi"]), bad
    return text, []
