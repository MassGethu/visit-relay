import json

import pytest

from asha.danger import (NOT_CHECKED, PRESENT, RULED_OUT, DangerChecker, _alternatives,
                         load_lexicon, vitals_signs)
from asha.text import DATA


def status(d, sign):
    return d.states[sign].status


def check(visit, text, lang="hi-IN", tested=("hi", "en")):
    d = DangerChecker(visit, tested_languages=tested)
    new = d.add_utterance(text, lang)
    return d, new


def test_every_sign_is_cited():
    for s in load_lexicon().signs.values():
        assert s.get("source") and s.get("page"), s["id"]


def test_lexicon_self_recall():
    """Every listed danger phrase must fire its own sign (number-only fragments excepted)."""
    lex = json.loads((DATA / "lexicon.json").read_text("utf-8"))
    misses = []
    total = 0
    for sign, langs in lex.items():
        for lang, entries in langs.items():
            if lang in ("notes", "negations"):
                continue
            for e in entries:
                for alt in {a for s in {e["script"], e["roman"]} for a in _alternatives(s)}:
                    if any(ch.isdigit() for ch in alt) or alt.strip() in {"ide", "hai"}:
                        continue
                    total += 1
                    d, _ = check(None, alt, tested=("hi", "kn", "en"))
                    if status(d, sign) != PRESENT:
                        misses.append((sign, alt))
    assert total > 750
    assert misses == []


def test_negation_phrases_never_fire_their_sign():
    lex = json.loads((DATA / "lexicon.json").read_text("utf-8"))
    wrong = []
    for sign, langs in lex.items():
        for e in langs.get("negations", []):
            for alt in {a for s in {e["script"], e["roman"]} for a in _alternatives(s, split_commas=False)}:
                d, _ = check(None, alt, tested=("hi", "kn", "en"))
                if status(d, sign) == PRESENT:
                    wrong.append((sign, alt))
    assert wrong == []


@pytest.mark.parametrize("visit,text,sign", [
    ("anc", "thoda khoon aa raha tha kal", "anc_vaginal_bleeding"),
    ("anc", "kal raat jhatke aa rahe the", "anc_convulsions"),
    ("hbnc", "bachcha doodh nahi pee raha", "nb_poor_feeding"),        # negator = danger
    ("hbnc", "magu haalu kudeetilla", "nb_poor_feeding"),
    ("anc", "baby movement kam hai", "anc_reduced_fetal_movement"),
    ("anc", "bleeding band ho gaya", "anc_vaginal_bleeding"),            # resolved, still refer
    ("anc", "bleeding jaasti illa aadru ide", "anc_vaginal_bleeding"),  # hedge: not much, but there
])
def test_present(visit, text, sign):
    d, new = check(visit, text)
    assert sign in new
    assert status(d, sign) == PRESENT


def test_resolved_is_history_not_absent():
    d, _ = check("anc", "bleeding pehle tha, ab nahi")
    row = next(r for r in d.receipt() if r["sign"] == "anc_vaginal_bleeding")
    assert row["status"] == PRESENT and row["history"] and row["needs_confirmation"]


def test_ruled_out_with_her_words():
    d, new = check("anc", "bleeding nahi hai")
    row = next(r for r in d.receipt() if r["sign"] == "anc_vaginal_bleeding")
    assert new == [] and row["status"] == RULED_OUT and "nahi" in row["quote"]


def test_negation_does_not_leak_across_signs():
    d, new = check("anc", "fits aaye, bleeding nahi")
    assert "anc_convulsions" in new
    assert status(d, "anc_vaginal_bleeding") == RULED_OUT


def test_shared_word_cannot_rule_out_another_sign():
    d, _ = check("anc", "sir dard bhi nahi")
    assert status(d, "anc_preterm_labour") == NOT_CHECKED


def test_fail_closed_in_untested_language():
    d, _ = check("anc", "bleeding illa", lang="kn-IN", tested=("hi", "en"))
    assert status(d, "anc_vaginal_bleeding") == NOT_CHECKED
    d, _ = check("anc", "bleeding illa", lang="kn-IN", tested=("hi", "kn", "en"))
    assert status(d, "anc_vaginal_bleeding") == RULED_OUT


def test_later_no_never_clears_a_danger_sign():
    d = DangerChecker("anc")
    d.add_utterance("thoda khoon aa raha tha")
    d.add_utterance("nahi nahi, bleeding nahi hai")
    row = next(r for r in d.receipt() if r["sign"] == "anc_vaginal_bleeding")
    assert row["status"] == PRESENT and row["disputed"] and row["needs_confirmation"]


def test_inverted_sign_normal_phrase_rules_out():
    d, new = check("hbnc", "bachcha theek se doodh pee raha hai")
    assert new == []


def test_receipt_covers_every_sign_in_scope():
    d, _ = check("anc", "wajan baavan kilo hai")
    rows = d.receipt()
    assert {r["sign"] for r in rows} == {s for s, m in load_lexicon().signs.items()
                                         if m["group"].startswith("pregnancy")}
    assert all(r["status"] == NOT_CHECKED for r in rows)


def test_safety_turn_has_at_most_three_and_doubtful_first():
    d = DangerChecker("anc")
    d.add_utterance("bleeding pehle tha, ab nahi")
    q = d.safety_questions()
    assert len(q) == 3 and q[0] == "anc_vaginal_bleeding"


def test_vitals():
    assert ("anc_high_bp", "BP 140/90") in vitals_signs({"bp": (140, 90)}, "anc")
    assert vitals_signs({"bp": (120, 80)}, "anc") == []
    nb = dict(vitals_signs({"temperature": (37.4, "C"), "breaths_per_min": 62, "weight_kg": 1.7}, "hbnc"))
    assert {"nb_fever", "nb_fast_breathing", "nb_very_low_birth_weight"} <= set(nb)
    assert dict(vitals_signs({"breaths_per_min": 45}, "hbyc", age_months=24))  # >= 40 over 12 months
    assert not vitals_signs({"breaths_per_min": 45}, "hbyc", age_months=6)     # < 50 under 12 months


def test_vitals_feed_the_receipt():
    d = DangerChecker("anc")
    d.add_utterance("BP ek sau pachaas by sau")
    assert d.add_vitals({"bp": (150, 100)}) == ["anc_high_bp"]


def test_negated_fits_amid_other_negations():
    d, new = check("anc", "fits nahi aaye, sir dard nahi hai, bukhaar nahi hai")
    assert new == []
    for sign in ("anc_convulsions", "anc_high_fever", "anc_severe_headache_blurred_vision"):
        assert status(d, sign) == RULED_OUT


def test_negated_kannada_verb_does_not_match_plain_word():
    _, new = check("anc", "agla visit 20 november ko aana hai")
    assert new == []


def test_stopped_yesterday_is_history():
    d, new = check("anc", "aur thoda khoon aa raha tha kal, ab nahi")
    row = next(r for r in d.receipt() if r["sign"] == "anc_vaginal_bleeding")
    assert new == ["anc_vaginal_bleeding"] and row["history"]


def test_feet_only_swelling_is_asked_not_alerted():
    d, new = check("anc", "pair mein thoda soojan hai shaam ko")
    assert new == [] and d.safety_questions()[0] == "anc_swelling_face_hands"
    d, new = check("anc", "chehre aur haathon mein soojan hai")
    assert new == ["anc_swelling_face_hands"]


@pytest.mark.parametrize("visit,text", [
    ("anc", "wajan baavan kilo hai"), ("anc", "IFA goli le rahi hai roz"),
    ("anc", "agla ANC check 20 tareekh ko"), ("anc", "TT ka teeka lag gaya"),
    ("anc", "sab theek hai, koi dikkat nahi"), ("anc", "hb das point do hai"),
    ("hbnc", "bachcha doodh theek se pee raha hai"), ("hbnc", "baby ka wajan do kilo aath sau"),
    ("hbnc", "naal sookh gayi hai"), ("hbnc", "BCG ka teeka lag gaya"),
    ("hbnc", "magu chennagi haalu kudeetide"),
])
def test_benign_sentences_do_not_alert(visit, text):
    _, new = check(visit, text)
    assert new == []
