"""Which visit is she talking about, and is she asking for something the app must not give?

Rules only, so the reply never waits for the LLM (the LLM adds a second opinion later):
  - out_of_scope(words): she asks for a medicine, a dose, a diagnosis or treatment.
  - context_cues(words, visit_type): clear words that this sentence belongs to another visit
    type ("pet mein bachcha" on a newborn visit, "teen saal ka" on an antenatal visit), plus any
    danger sign from another visit's checklist when nothing on this visit's checklist matched.
  - answer_to_switch(words): her spoken reply to "switch the visit?" (yes / no / a visit name).
"""
from __future__ import annotations

from .danger import VISIT_GROUPS, DangerChecker

VISIT_TYPES = ("anc", "pnc", "hbnc", "hbyc")
SUBJECTS = {"anc": "mother", "pnc": "mother", "hbnc": "newborn", "hbyc": "child"}
# HBNC visits cover the mother after delivery as well as the newborn.
COVERS = {"hbnc": {"pnc"}}

# ---------- out of scope: medicine, dose, diagnosis, treatment ----------

MEDICINE_WORDS = {"dawa", "dawai", "dawaai", "davai", "davaa", "दवा", "दवाई", "दवाइ", "दवाएं", "medicine",
                  "medicines", "ಔಷಧ", "ಔಷಧಿ", "aushadha", "aushadhi", "dose", "खुराक", "khuraak", "khurak",
                  "ilaaj", "ilaj", "इलाज", "treatment", "ಚಿಕಿತ್ಸೆ", "bimari", "beemari", "बीमारी", "rog",
                  "रोग", "ರೋಗ", "diagnosis", "injection", "इंजेक्शन", "syrup", "सिरप"}
ASK_WORDS = {"kaun", "kaunsi", "kaunsa", "konsi", "konsa", "kya", "kitni", "kitna", "kaise", "kaisi",
             "कौन", "कौनसी", "कौनसा", "क्या", "कितनी", "कितना", "कैसे", "which", "what", "how", "should",
             "ಯಾವ", "ಏನು", "ಎಷ್ಟು", "yaava", "yenu", "eshtu", "dein", "de", "doon", "du", "dena", "khilayein",
             "दें", "दूँ", "दूं", "देना", "khilaun", "pilayein", "batao", "bataiye", "बताओ", "बताइए", "suggest"}


def out_of_scope(words: list[str]) -> bool:
    """"Kaunsi dawai dein?", "bukhaar ki dawa batao", "kya bimari hai?" — never answered."""
    return bool(set(words) & MEDICINE_WORDS) and bool(set(words) & ASK_WORDS)


# ---------- context cues ----------

CUE_WORDS = {
    "anc": {"pregnant", "pregnancy", "garbh", "garbhvati", "garbhavati", "garbhini", "गर्भ", "गर्भवती",
            "गर्भावस्था", "ಗರ್ಭ", "ಗರ್ಭಿಣಿ", "ಗರ್ಭಿಣಿಯರ"},
    "pnc": {"prasuta", "प्रसूता", "bananthi", "baanantiy", "ಬಾಣಂತಿ"},
    "hbnc": {"navjaat", "navjat", "नवजात", "newborn", "ನವಜಾತ", "hasugusu", "ಹಸುಗೂಸು"},
    "hbyc": {"toddler"},
}
CUE_SEQS = {
    "anc": [("pet", "mein", "bachcha"), ("pet", "mein", "baby"), ("पेट", "में", "बच्चा"), ("हॉटे", "ಮಗು")],
    "pnc": [("delivery", "ho", "gayi"), ("delivery", "ke", "baad"), ("prasav", "ke", "baad"),
            ("प्रसव", "के", "बाद"), ("डिलीवरी", "के", "बाद"), ("डिलीवरी", "हो", "गई"), ("ಹೆರಿಗೆ", "ಆದ"),
            ("ಹೆರಿಗೆ", "ನಂತರ")],
    "hbnc": [("din", "ka"), ("din", "ki"), ("दिन", "का"), ("दिन", "की"), ("ದಿನದ", "ಮಗು")],
    "hbyc": [("saal", "ka"), ("saal", "ki"), ("साल", "का"), ("साल", "की"), ("varsha", "magu"),
             ("ವರ್ಷದ", "ಮಗು"), ("mahine", "ka", "bachcha"), ("महीने", "का", "बच्चा")],
}
# "baby ko bukhaar" on a pregnancy or mother's visit: about a child, not the woman ("bachcha hil
# nahi raha" alone is the baby in the womb, so only "<child word> ko / ka / ki" counts)
CHILD_WORDS = {"baby", "bachcha", "bachche", "bacche", "bachchi", "बच्चा", "बच्चे", "बच्ची", "शिशु", "shishu",
               "ಮಗು", "ಮಗುವಿಗೆ", "ಮಗುವಿನ", "magu", "maguvige", "child", "kid"}
CHILD_POSTPOSITIONS = {"ko", "ka", "ki", "ke", "को", "का", "की", "के", "has", "is"}
MAX_HINTED_TYPES = 2
CHILD_VISITS = {"anc": {"hbnc", "hbyc"}, "pnc": {"hbnc"}}
_GROUP_TO_TYPES = {g: {vt for vt, gs in VISIT_GROUPS.items() if g in gs}
                   for gs in VISIT_GROUPS.values() for g in gs}


def _has(words: list[str], seq: tuple[str, ...]) -> bool:
    n = len(seq)
    return any(tuple(words[i:i + n]) == seq for i in range(len(words) - n + 1))


def _about_a_child(words: list[str]) -> bool:
    return any(w in CHILD_WORDS and (w in ("ಮಗುವಿಗೆ", "ಮಗುವಿನ", "maguvige")
                                     or (i + 1 < len(words) and words[i + 1] in CHILD_POSTPOSITIONS))
               for i, w in enumerate(words))


def context_cues(words: list[str], text: str, visit_type: str, matched_here: bool,
                 language_code: str = "hi-IN") -> set[str]:
    """Visit types (other than this one) that the sentence clearly points to.
    matched_here: the sentence mentioned a sign on this visit's own checklist."""
    found = {vt for vt, cues in CUE_WORDS.items() if set(words) & cues}
    if _about_a_child(words):
        found |= CHILD_VISITS.get(visit_type, set())
    found |= {vt for vt, seqs in CUE_SEQS.items() if any(_has(words, s) for s in seqs)}
    if "anc" in found:
        found -= {"hbyc", "hbnc"}       # "saat mahine ki garbhvati", "pet mein bachcha": still pregnancy
    if not matched_here:                # a sign from another checklist, and none from this one
        probe = DangerChecker(None)
        hinted = set()
        for sign in probe.add_utterance(text, language_code):
            hinted |= _GROUP_TO_TYPES.get(probe.lex.signs[sign]["group"], set())
        hinted -= {visit_type} | COVERS.get(visit_type, set())
        if len(hinted) <= MAX_HINTED_TYPES:      # a sign on most checklists says nothing about which visit
            found |= hinted
    return {vt for vt in found if vt != visit_type and vt not in COVERS.get(visit_type, set())}


# ---------- her answer to "switch the visit?" ----------

YES = {"haan", "haa", "ha", "han", "हाँ", "हां", "हा", "ಹೌದು", "howdu", "haudu", "yes", "badlo", "बदलो",
       "badal", "बदल", "ok", "okay", "sari", "ಸರಿ", "ಬದಲಿಸಿ", "badalisi", "switch", "change"}
NO = {"nahi", "nahin", "na", "नहीं", "ना", "illa", "ಇಲ್ಲ", "beda", "ಬೇಡ", "no", "mat", "मत"}
FILLER = {"ji", "जी", "theek", "ठीक", "hai", "है", "karo", "करो", "kar", "do", "दो", "dijiye", "दीजिए",
          "please", "visit", "वाला", "wala", "wali", "वाली", "ki", "ka", "की", "का", "ಭೇಟಿ", "it", "to"}
TYPE_WORDS = {
    "anc": {"anc", "garbhavastha", "garbh", "गर्भावस्था", "गर्भ", "pregnancy", "antenatal", "ಗರ್ಭಿಣಿ", "garbhini"},
    "pnc": {"pnc", "prasav", "प्रसव", "postnatal", "ಬಾಣಂತಿ", "maa", "माँ", "मां", "mother"},
    "hbnc": {"hbnc", "navjaat", "नवजात", "newborn", "ನವಜಾತ", "shishu", "शिशु"},
    "hbyc": {"hbyc", "child", "toddler", "ಚಿಕ್ಕ", "chhote", "chhota", "छोटे", "छोटा", "young"},
}
_ALL_TYPE_WORDS = set().union(*TYPE_WORDS.values())
MAX_ANSWER_WORDS = 5


def answer_to_switch(words: list[str]) -> str | None:
    """A visit type she names, "yes", "no", or None if this is not an answer to the question.
    "bukhaar nahi hai" is a checklist answer, not "no": every word must be an answer word."""
    if not words or len(words) > MAX_ANSWER_WORDS:
        return None
    if set(words) - _ALL_TYPE_WORDS - YES - NO - FILLER:
        return None
    named = {vt for vt, ws in TYPE_WORDS.items() if set(words) & ws}
    if len(named) == 1 and not set(words) & NO:
        return named.pop()
    if named:
        return None
    yes, no = bool(set(words) & YES), bool(set(words) & NO)
    if yes != no:
        return "yes" if yes else "no"
    return None
