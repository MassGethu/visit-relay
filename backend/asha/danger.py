"""Danger-sign layer: lexicon matching with per-sign polarity, and the danger-sign receipt.

Design rules, from research/01-danger-signs.md:
- Every sign is cited (source + page) in data/danger_signs.json.
- Negation is modelled per sign. For "inverted" signs the danger phrase itself
  contains a negator ("doodh nahi pee raha"), so "nahi" means danger there.
- "band ho gaya" / "ab nahi" after a danger phrase means *resolved*, not absent:
  it is still recorded as present (history) because earlier bleeding or fits
  still warrant referral.
- Hedges ("thoda thoda", "swalpa", "aadru ide") never negate.
- When unsure, surface the sign to the ASHA; never drop it.

The receipt gives every sign checked on a visit one of three statuses:
  present      a danger phrase matched (an alert fires immediately)
  ruled_out    absent in her own words, with the quote, in a tested language
  not_checked  nothing was said, or it was said in a language we have not evaluated
There is no silent "no".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

import re

from .text import DATA, Token, fold, similar, tokens

PRESENT, RULED_OUT, NOT_CHECKED = "present", "ruled_out", "not_checked"

VISIT_GROUPS = {
    "anc": ("pregnancy", "pregnancy (labour)"),
    "pnc": ("postnatal",),
    "hbnc": ("postnatal", "newborn"),
    "hbyc": ("child_u5",),
}

# Asked in the single safety turn when she did not mention them (most urgent first).
CORE_SIGNS = {
    "pregnancy": ["anc_vaginal_bleeding", "anc_convulsions", "anc_severe_headache_blurred_vision",
                  "anc_high_fever", "anc_swelling_face_hands", "anc_reduced_fetal_movement",
                  "anc_water_break_no_labour", "anc_severe_abdominal_pain"],
    "postnatal": ["pnc_heavy_bleeding", "pnc_convulsions_unconscious", "pnc_fever",
                  "pnc_breathing_difficulty", "pnc_foul_lochia"],
    "newborn": ["nb_poor_feeding", "nb_convulsions", "nb_fast_breathing", "nb_lethargy_limp",
                "nb_fever", "nb_hypothermia", "nb_jaundice_severe", "nb_umbilical_infection"],
    "child_u5": ["ch_unable_to_drink", "ch_vomits_everything", "ch_convulsions",
                 "ch_lethargic_unconscious", "ch_chest_indrawing", "ch_fast_breathing"],
}

STOPWORDS = {
    # Hindi auxiliaries, postpositions, light verbs
    "hai", "hain", "h", "tha", "thi", "the", "ho", "raha", "rahi", "rahe", "rha", "rhi",
    "ka", "ki", "ke", "ko", "se", "mein", "me", "main", "par", "pe", "ek", "bhi", "to", "ji",
    "aur", "ya", "hi", "aa", "aaya", "aayi", "aaye", "aata", "aati", "ja", "jaa", "jata",
    "jaata", "gaya", "gayi", "gaye", "hua", "hui", "hue", "hota", "hoti", "hona", "jana",
    "है", "हैं", "था", "थी", "थे", "हो", "रहा", "रही", "रहे", "का", "की", "के", "को", "से",
    "में", "पर", "एक", "भी", "आ", "जा", "गया", "गई", "गए", "हुआ", "हुई", "जाना",
    # Kannada auxiliaries
    "ide", "ive", "ittu", "aagide", "aagtide", "aagtaa", "ಇದೆ", "ಇತ್ತು", "ಆಗಿದೆ",
    # English fillers
    "is", "are", "was", "the", "a", "an", "has", "have", "of", "in", "on", "and", "or", "it",
}
NEGATORS = {"nahi", "nahin", "nahī", "na", "nai", "no", "not", "never", "illa", "nahi.",
            "नहीं", "नही", "ना", "ಇಲ್ಲ"}
POLARITY_WORDS = {"band", "बंद", "kam", "kammi", "kadime", "कम", "ಕಡಿಮೆ", "ruk", "stop", "stopped"}
HEDGES = [("thoda", "thoda"), ("kabhi", "kabhi"), ("swalpa",), ("ಸ್ವಲ್ಪ",), ("aadru",),
          ("aadaru",), ("lekin", "hai"), ("but", "there")]
RESOLVED = [("ab", "nahi"), ("ab", "nahin"), ("iga", "illa"), ("ivaga", "illa"), ("band", "ho"),
            ("ruk", "gaya"), ("ruk", "gayi"), ("nintide",), ("nintu",), ("ನಿಂತಿದೆ",),
            ("अब", "नहीं"), ("बंद", "हो"), ("ಈಗ", "ಇಲ್ಲ")]
CLAUSE_BREAKS = {"lekin", "magar", "par", "but", "aur", "and", "mattu", "aadre", "phir",
                 "लेकिन", "और", "ಆದರೆ", "ಮತ್ತು"}


# research/01 note: feet-only swelling is common late in pregnancy and is NOT the official
# sign ("record, don't auto-flag"). It is asked about in the safety turn instead.
SWELLING_SIGNS = {"anc_swelling_face_hands", "pnc_swelling_face_hands"}
FEET_WORDS = {"pair", "pairon", "paon", "paav", "kaalu", "kaal", "feet", "foot", "leg", "legs", "ankle",
              "पैर", "पैरों", "ಕಾಲು"}
FACE_HAND_WORDS = {"chehra", "chehre", "munh", "muh", "haath", "haathon", "face", "hand", "hands",
                   "mukha", "kai", "चेहरे", "हाथ", "मुँह", "ಮುಖ", "ಕೈ"}


def is_negator(word: str) -> bool:
    return word in NEGATORS or word.endswith("illa") or word.endswith("ಲ್ಲ") or fold(word) == "nahi"


# ───────────────────────── phrase compilation ─────────────────────────

@dataclass(frozen=True)
class Phrase:
    sign: str
    slots: tuple[frozenset[str], ...]   # each slot is a set of interchangeable words
    mandatory: tuple[bool, ...]         # polarity-carrying slots can never be skipped
    source_text: str
    negation: bool                      # True if this phrase says the sign is absent


def _alternatives(text: str, split_commas: bool = True) -> list[str]:
    text = text.replace("~", " ")
    alts: list[str] = []
    for paren in re.findall(r"\(([^)]*)\)", text):
        if "—" not in paren and "ambiguous" not in paren and "only" not in paren:
            alts.append(paren)
    text = re.sub(r"\([^)]*\)", " ", text)
    pattern = r"\s+/\s*|\s*/\s+|;\s+" + (r"|,\s+" if split_commas else "")
    for chunk in re.split(pattern, text):
        if chunk.strip():
            alts.append(chunk)
    return alts


def _slots(chunk: str) -> list[frozenset[str]]:
    slots = []
    for part in chunk.split():
        options = {t.text for piece in part.split("/") for t in tokens(piece)}
        options = {o for o in options if o not in STOPWORDS and not o.replace(".", "").isdigit()}
        if options:
            slots.append(frozenset(options))
    return slots


def _compile(sign: str, entry: dict, negation: bool, inverted: bool) -> list[Phrase]:
    out = []
    for surface in {entry["script"], entry["roman"]}:
        for chunk in _alternatives(surface, split_commas=not negation):
            if re.search(r"\d", chunk):
                continue  # "HB 6 hai", "102 hai": number-defined, handled by vitals_signs()
            slots = _slots(chunk)
            if not slots or (negation and len(slots) < 2):
                continue  # a one-word "absent" phrase ("theek hai") is too weak to rule anything out
            mandatory = tuple(
                any(is_negator(w) for w in s) or (inverted and bool(s & POLARITY_WORDS))
                for s in slots)
            out.append(Phrase(sign, tuple(slots), mandatory, chunk.strip(), negation))
    return out


@dataclass
class Lexicon:
    signs: dict[str, dict]
    inverted: frozenset[str]
    phrases: list[Phrase]
    generic: frozenset[str]   # words too common to carry a partial match on their own
    word_signs: dict[str, set[str]] = field(default_factory=dict)  # fold(word) -> signs using it
    by_word: dict[str, list[int]] = field(default_factory=dict)   # slot word -> phrase indices
    by_initial: dict[str, list[tuple[str, str]]] = field(default_factory=dict)  # fold[0] -> (word, fold)


@lru_cache(maxsize=1)
def load_lexicon() -> Lexicon:
    signs = {s["id"]: s for s in json.loads((DATA / "danger_signs.json").read_text("utf-8"))}
    lex = json.loads((DATA / "lexicon.json").read_text("utf-8"))
    inverted = frozenset((DATA / "inverted.txt").read_text("utf-8").split())
    phrases: list[Phrase] = []
    for sign, langs in lex.items():
        for lang, entries in langs.items():
            if lang == "notes":
                continue
            for e in entries:
                phrases.extend(_compile(sign, e, lang == "negations", sign in inverted))
    # A word used by phrases of 4+ different signs ("bachcha", "magu", "baby") is generic.
    by_word: dict[str, set[str]] = {}
    for p in phrases:
        for s in p.slots:
            for w in s:
                by_word.setdefault(fold(w), set()).add(p.sign)
    generic = {w for w, ss in by_word.items() if len(ss) >= 4}
    generic |= ALWAYS_GENERIC
    return _finish(signs, inverted, phrases, generic, by_word)


ALWAYS_GENERIC = {fold(w) for w in ("bachcha", "baccha", "baby", "magu", "maguvu", "amma", "maa",
                                  "thoda", "bahut", "tumba", "jaasti", "kam", "kammi", "kal",
                                  "body", "pet", "hotte", "बच्चा", "ಮಗು")}


def _finish(signs, inverted, phrases, generic, by_word) -> Lexicon:
    index: dict[str, list[int]] = {}
    for n, p in enumerate(phrases):
        for slot in p.slots:
            for w in slot:
                index.setdefault(w, []).append(n)
    by_initial: dict[str, list[tuple[str, str]]] = {}
    for w in index:
        f = fold(w)
        by_initial.setdefault(f[:1], []).append((w, f))
    return Lexicon(signs, inverted, phrases, frozenset(generic), word_signs=by_word,
                   by_word=index, by_initial=by_initial)


def _token_hits(lex: Lexicon, toks: list[Token]) -> dict[str, set[int]]:
    """Which lexicon words each token could be (exact, folded, or fuzzy)."""
    hits: dict[str, set[int]] = {}
    for t in toks:
        if t.text in STOPWORDS:
            continue
        ft = fold(t.text)
        for w, fw in lex.by_initial.get(ft[:1], []):
            # a negated word ("aagilla") only matches a negated token, never "agla"
            if (abs(len(fw) - len(ft)) <= 3 and is_negator(w) == is_negator(t.text)
                    and similar(t.text, w)):
                hits.setdefault(w, set()).add(t.index)
    return hits


# ───────────────────────── matching ─────────────────────────

@dataclass
class Match:
    sign: str
    start: int
    end: int
    partial: bool
    negation_phrase: bool
    phrase: str
    specific: bool = True   # at least one matched word is not a generic one ("dard", "bachcha")


def _find(phrase: Phrase, content: list[int], hits: dict[str, set[int]],
          generic: frozenset[str]) -> Match | None:
    """Best occurrence of the phrase in the content tokens (indices into the token list)."""
    k = len(phrase.slots)
    slot_pos = [set().union(*(hits.get(w, set()) for w in slot)) for slot in phrase.slots]
    anchors = sorted(set().union(*slot_pos))
    best: Match | None = None
    for a in anchors:
        span = set(c for c in content[content.index(a): content.index(a) + k + 3])
        used: set[int] = set()
        found: list[int | None] = []
        for pos in slot_pos:
            p = min((x for x in pos & span if x not in used), default=None)
            found.append(p)
            if p is not None:
                used.add(p)
        missing = [n for n, f in enumerate(found) if f is None]
        if phrase.negation and not missing and found != sorted(found):
            continue  # "absent" phrases must keep their word order ("bleeding ... nahi")
        matched_words = [w for n, slot in enumerate(phrase.slots) if found[n] is not None for w in slot]
        if not missing:
            partial = False
        elif (k >= 2 and len(missing) == 1 and not phrase.mandatory[missing[0]] and not phrase.negation
              and any(not is_negator(w) for w in matched_words)
              and (k - 1 >= 3 or any(fold(w) not in generic and len(fold(w)) >= 4 and not is_negator(w)
                                     for w in matched_words))):
            partial = True
        else:
            continue
        got = [f for f in found if f is not None]
        specific = any(fold(w) not in generic and len(fold(w)) >= 3 for w in matched_words)
        m = Match(phrase.sign, min(got), max(got), partial, phrase.negation, phrase.source_text, specific)
        if best is None or (best.partial and not partial):
            best = m
        if not partial:
            break
    return best


def _has_seq(words: list[str], seq: tuple[str, ...]) -> bool:
    n = len(seq)
    return any(all(similar(words[i + j], seq[j]) for j in range(n)) for i in range(len(words) - n + 1))


@dataclass
class Evidence:
    status: str
    quote: str
    utterance: int
    partial: bool = False
    history: bool = False
    phrase: str = ""


@dataclass
class SignState:
    sign: str
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(e.status == PRESENT for e in self.evidence):
            return PRESENT              # a later "no" can never clear a danger sign
        if any(e.status == RULED_OUT for e in self.evidence):
            return RULED_OUT
        return NOT_CHECKED

    @property
    def disputed(self) -> bool:
        kinds = {e.status for e in self.evidence}
        return PRESENT in kinds and RULED_OUT in kinds

    @property
    def needs_confirmation(self) -> bool:
        present = [e for e in self.evidence if e.status == PRESENT]
        return self.disputed or (bool(present) and all(e.partial or e.history for e in present))


class DangerChecker:
    """Runs on every final transcript of a visit and keeps the receipt.

    tested_languages: base language codes for which our evaluation has shown the
    lexicon works. "Ruled out" is only recorded in those; anywhere else the sign
    stays not_checked (fail closed). Add "kn" only after the Kannada eval passes.
    """

    def __init__(self, visit_type: str | None = None, tested_languages=("hi", "en")):
        self.lex = load_lexicon()
        self.visit_type = visit_type
        groups = VISIT_GROUPS.get(visit_type or "", None)
        self.scope = [s for s, d in self.lex.signs.items() if groups is None or d["group"] in groups]
        self.tested = {l.split("-")[0] for l in tested_languages}
        self.states = {s: SignState(s) for s in self.scope}
        # "Generic" is judged within this visit's signs: "bukhaar" is shared by the mother,
        # newborn and child fever signs, but on an ANC visit it names one sign.
        if groups is None:
            self.generic = self.lex.generic
        else:
            scope = set(self.scope)
            self.generic = frozenset({w for w, ss in self.lex.word_signs.items() if len(ss & scope) >= 3}
                                     | ALWAYS_GENERIC)
        self.utterances: list[str] = []
        self.to_ask: list[str] = []   # mentioned in a way that is not the official sign: ask once

    # one final transcript in, newly present signs out (these must alert at once)
    def add_utterance(self, text: str, language_code: str = "hi-IN") -> list[str]:
        idx = len(self.utterances)
        self.utterances.append(text)
        toks = tokens(text)
        words = [t.text for t in toks]
        lang_ok = language_code.split("-")[0] in self.tested
        scope = set(self.scope)

        hits = _token_hits(self.lex, toks)
        content = [t.index for t in toks if t.text not in STOPWORDS]
        candidates = sorted({n for w in hits for n in self.lex.by_word[w]})
        matches = [m for n in candidates if (p := self.lex.phrases[n]).sign in scope
                   if (m := _find(p, content, hits, self.generic))]
        # A "normal" phrase for an inverted sign ("bachcha theek se hil raha") only counts
        # if no negator sits inside it; otherwise it is the danger phrase misheard as normal.
        # "Absent" phrases are not trusted when she hedges or says it stopped
        # ("pehle tha, ab nahi"): the danger phrase is then judged by _polarity.
        hedged = any(_has_seq(words, h) for h in HEDGES + RESOLVED)
        neg_spans = {(m.sign, m.start, m.end) for m in matches if m.negation_phrase and m.specific
                     and not hedged
                     and not (m.sign in self.lex.inverted
                              and any(is_negator(w) for w in words[m.start:m.end + 1]))}
        danger = [m for m in matches if not m.negation_phrase]
        starts = sorted({m.start for m in danger if not is_negator(words[m.start])})

        newly: list[str] = []
        before = {s: self.states[s].status for s in scope}
        per_sign: dict[str, list[Evidence]] = {}
        for m in danger:
            covered = any(s == m.sign and a <= m.start and m.end <= b for s, a, b in neg_spans)
            if covered:
                continue
            quote = " ".join(words[max(0, m.start - 2): m.end + 4])
            ev = self._polarity(m, words, starts, idx, quote)
            if ev is not None:
                per_sign.setdefault(m.sign, []).append(ev)
        for sign, a, b in neg_spans:
            quote = " ".join(words[max(0, a - 2): b + 3])
            per_sign.setdefault(sign, []).append(Evidence(RULED_OUT, quote, idx, phrase="negation"))

        wordset = set(words)
        for sign in SWELLING_SIGNS & set(per_sign):
            if wordset & FEET_WORDS and not wordset & FACE_HAND_WORDS:
                per_sign.pop(sign)
                if sign not in self.to_ask:
                    self.to_ask.append(sign)
        for sign, evs in per_sign.items():
            # strongest single piece of evidence per utterance: present > ruled_out
            present = [e for e in evs if e.status == PRESENT]
            chosen = sorted(present, key=lambda e: (e.partial, e.history))[:1] if present else evs[:1]
            for e in chosen:
                if e.status == RULED_OUT and not lang_ok:
                    continue  # fail closed: not evaluated in this language
                self.states[sign].evidence.append(e)
        for s in scope:
            if before[s] != PRESENT and self.states[s].status == PRESENT:
                newly.append(s)
        return newly

    def _polarity(self, m: Match, words: list[str], starts: list[int], idx: int,
                  quote: str) -> Evidence | None:
        if m.sign in self.lex.inverted:
            return Evidence(PRESENT, quote, idx, partial=m.partial, phrase=m.phrase)
        # look for a negator just before or just after the phrase, inside the clause,
        # and not past the start of another sign's phrase
        barrier = next((s for s in starts if s > m.end), len(words))
        lo = m.start
        for _ in range(2):
            if lo - 1 >= 0 and words[lo - 1] not in CLAUSE_BREAKS:
                lo -= 1
        hi = m.end
        for j in range(m.end + 1, min(len(words), m.end + 4, barrier)):
            if words[j] in CLAUSE_BREAKS:
                break
            hi = j
        window = words[lo:hi + 1]
        negated = any(is_negator(w) for w in words[lo:m.start] + words[m.end + 1:hi + 1])
        clause = words[lo: min(len(words), m.end + 8, barrier + 2)]
        if any(_has_seq(clause, h) for h in RESOLVED):
            # happened, now stopped: still present (earlier bleeding/fits warrant referral)
            return Evidence(PRESENT, quote, idx, partial=m.partial, history=True, phrase=m.phrase)
        if not negated:
            return Evidence(PRESENT, quote, idx, partial=m.partial, phrase=m.phrase)
        if any(_has_seq(window + words[hi + 1: hi + 3], h) for h in HEDGES):
            return Evidence(PRESENT, quote, idx, partial=m.partial, phrase=m.phrase)
        if m.partial or not m.specific:
            return None  # too weak to rule anything out: leave it not_checked
        return Evidence(RULED_OUT, quote, idx, phrase=m.phrase)

    # ───────── outputs ─────────

    def add_vitals(self, measurements: dict, age_months: float | None = None) -> list[str]:
        """Danger signs defined by a number she read out (BP, temperature, breaths, weight)."""
        hits = vitals_signs(measurements, self.visit_type, age_months)
        newly = []
        for sign, quote in hits:
            if sign not in self.states:
                continue
            was = self.states[sign].status
            self.states[sign].evidence.append(Evidence(PRESENT, quote, len(self.utterances) - 1,
                                                       phrase="measured value"))
            if was != PRESENT:
                newly.append(sign)
        return newly

    def receipt(self) -> list[dict]:
        rows = []
        for s in self.scope:
            st, meta = self.states[s], self.lex.signs[s]
            last = next((e for e in reversed(st.evidence) if e.status == st.status), None)
            rows.append({
                "sign": s, "status": st.status, "quote": last.quote if last else None,
                "history": bool(last and last.history), "disputed": st.disputed,
                "needs_confirmation": st.needs_confirmation, "urgency": meta.get("urgency"),
                "source": meta.get("source"), "page": meta.get("page"),
            })
        return rows

    def present(self) -> list[str]:
        return [s for s in self.scope if self.states[s].status == PRESENT]

    def safety_questions(self, limit: int = 3) -> list[str]:
        """Signs for the single safety turn: doubtful ones first, then unmentioned core signs."""
        doubtful = [s for s in self.scope if self.states[s].needs_confirmation]
        doubtful += [s for s in self.to_ask if s not in doubtful and self.states[s].status == NOT_CHECKED]
        core = [s for g in (VISIT_GROUPS.get(self.visit_type or "", ()) or ())
                for s in CORE_SIGNS.get(g, [])
                if s in self.states and self.states[s].status == NOT_CHECKED]
        return (doubtful + [s for s in core if s not in doubtful])[:limit]


def vitals_signs(m: dict, visit_type: str | None, age_months: float | None = None) -> list[tuple[str, str]]:
    """Thresholds from the cited sources; where sources conflict, the more sensitive one."""
    out: list[tuple[str, str]] = []
    temp_f = None
    if m.get("temperature"):
        v, unit = m["temperature"]
        temp_f = v if unit == "F" else v * 9 / 5 + 32
    groups = VISIT_GROUPS.get(visit_type or "", ("pregnancy", "postnatal", "newborn", "child_u5"))
    if "pregnancy" in groups:
        if m.get("bp") and (m["bp"][0] >= 140 or m["bp"][1] >= 90):
            out.append(("anc_high_bp", f"BP {m['bp'][0]}/{m['bp'][1]}"))
        if temp_f and temp_f > 100:
            out.append(("anc_high_fever", f"temperature {temp_f:.1f} F"))
    if "postnatal" in groups and temp_f and temp_f > 102:
        out.append(("pnc_fever", f"mother temperature {temp_f:.1f} F"))
    if "newborn" in groups:
        if temp_f and temp_f > 99:
            out.append(("nb_fever", f"temperature {temp_f:.1f} F"))
        if temp_f and temp_f < 95.9:
            out.append(("nb_hypothermia", f"temperature {temp_f:.1f} F"))
        if m.get("breaths_per_min") and m["breaths_per_min"] >= 60:
            out.append(("nb_fast_breathing", f"{m['breaths_per_min']} breaths/min"))
        if m.get("weight_kg") and m["weight_kg"] < 1.8:
            out.append(("nb_very_low_birth_weight", f"weight {m['weight_kg']} kg"))
    if "child_u5" in groups and m.get("breaths_per_min"):
        limit = 50 if age_months is not None and age_months < 12 else 40
        if m["breaths_per_min"] >= limit:
            out.append(("ch_fast_breathing", f"{m['breaths_per_min']} breaths/min"))
    return out


def sign_label(sign: str) -> str:
    """Short English label from the first official wording, for screens and logs."""
    wording = load_lexicon().signs[sign].get("official_wording", sign)
    first = wording.split('"')[1] if wording.count('"') >= 2 else wording
    return first.strip()
