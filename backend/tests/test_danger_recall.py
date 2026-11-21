"""Recall regression: natural ASHA sentences, Roman and Devanagari (Prisma writes Hindi in Devanagari).

Every sentence here must keep working. Add the failures found on recorded clips (eval/) to these lists.
"""
import pytest

from asha.danger import DangerChecker

POS = [  # (visit_type, sentence, sign)
 ("anc", "thoda khoon aa raha hai", "anc_vaginal_bleeding"),
 ("anc", "थोड़ा खून आ रहा है", "anc_vaginal_bleeding"),
 ("anc", "neeche se khoon gira", "anc_vaginal_bleeding"),
 ("anc", "bleeding ho rahi hai", "anc_vaginal_bleeding"),
 ("anc", "bachcha pet mein hil nahi raha", "anc_reduced_fetal_movement"),
 ("anc", "बच्चा पेट में हिल नहीं रहा", "anc_reduced_fetal_movement"),
 ("anc", "baby movement kam hai", "anc_reduced_fetal_movement"),
 ("anc", "sar mein bahut dard hai aur dhundhla dikh raha hai", "anc_severe_headache_blurred_vision"),
 ("anc", "सिर में बहुत दर्द है", "anc_severe_headache_blurred_vision"),
 ("anc", "chehre aur haath pe sujan hai", "anc_swelling_face_hands"),
 ("anc", "चेहरे पर सूजन है", "anc_swelling_face_hands"),
 ("anc", "use daura pada", "anc_convulsions"),
 ("anc", "झटके आए", "anc_convulsions"),
 ("anc", "tez bukhaar hai", "anc_high_fever"),
 ("anc", "तेज़ बुखार है", "anc_high_fever"),
 ("anc", "pet mein bahut tez dard hai", "anc_severe_abdominal_pain"),
 ("anc", "पेट में बहुत दर्द है", "anc_severe_abdominal_pain"),
 ("anc", "saans phool rahi hai", "anc_breathlessness"),
 ("anc", "सांस फूल रही है", "anc_breathlessness"),
 ("anc", "paani ki thaili phat gayi", "anc_water_break_no_labour"),
 ("pnc", "bahut zyada khoon ja raha hai", "pnc_heavy_bleeding"),
 ("pnc", "बहुत ज़्यादा खून जा रहा है", "pnc_heavy_bleeding"),
 ("pnc", "badboodar paani aa raha hai", "pnc_foul_lochia"),
 ("pnc", "bukhaar hai", "pnc_fever"),
 ("pnc", "बुखार है", "pnc_fever"),
 ("pnc", "pishab nahi ho raha", "pnc_no_urine"),
 ("pnc", "स्तन में दर्द और बुखार", "pnc_breast_problem_fever"),
 ("pnc", "khana nahi kha rahi, ulti ho rahi hai", "pnc_not_eating_vomiting"),
 ("hbnc", "baby doodh nahi pee raha", "nb_poor_feeding"),
 ("hbnc", "बच्चा दूध नहीं पी रहा", "nb_poor_feeding"),
 ("hbnc", "doodh nahi pi raha hai", "nb_poor_feeding"),
 ("hbnc", "baby feed nahi le raha", "nb_poor_feeding"),
 ("hbnc", "stanpan nahi kar raha", "nb_poor_feeding"),
 ("hbnc", "baby tez tez saans le raha hai", "nb_fast_breathing"),
 ("hbnc", "बच्चा तेज़ तेज़ सांस ले रहा है", "nb_fast_breathing"),
 ("hbnc", "pasli chal rahi hai", "nb_chest_indrawing"),
 ("hbnc", "पसली चल रही है", "nb_chest_indrawing"),
 ("hbnc", "baby ko bukhaar hai", "nb_fever"),
 ("hbnc", "बच्चे को बुखार है", "nb_fever"),
 ("hbnc", "baby bilkul thanda hai", "nb_hypothermia"),
 ("hbnc", "बच्चा ठंडा पड़ गया है", "nb_hypothermia"),
 ("hbnc", "baby dheela pad gaya hai", "nb_lethargy_limp"),
 ("hbnc", "बच्चा सुस्त है", "nb_lethargy_limp"),
 ("hbnc", "rona bahut kamzor hai", "nb_weak_cry"),
 ("hbnc", "baby ko jhatke aa rahe hain", "nb_convulsions"),
 ("hbnc", "बच्चे को झटके आ रहे हैं", "nb_convulsions"),
 ("hbnc", "aankh aur hatheli peeli hai", "nb_jaundice_severe"),
 ("hbnc", "हथेली और तलवे पीले हैं", "nb_jaundice_severe"),
 ("hbnc", "naal se mawaad aa raha hai", "nb_umbilical_infection"),
 ("hbnc", "नाल लाल है और पस आ रहा है", "nb_umbilical_infection"),
 ("hbnc", "baby neela pad gaya", "nb_cyanosis"),
 ("hbnc", "पेशाब नहीं किया", "nb_no_urine_stool"),
 ("hbyc", "bachcha kuch bhi pee nahi pa raha", "ch_unable_to_drink"),
 ("hbyc", "sab kuch ulti kar deta hai", "ch_vomits_everything"),
 ("hbyc", "सब कुछ उल्टी कर देता है", "ch_vomits_everything"),
 ("hbyc", "bachche ko jhatke aaye", "ch_convulsions"),
 ("hbyc", "pasli chal rahi hai", "ch_chest_indrawing"),
 ("hbyc", "saat din se bukhaar hai", "ch_fever_persistent"),
 ("hbyc", "दस्त में खून आ रहा है", "ch_blood_in_stool"),
 ("hbyc", "do hafte se dast ho rahe hain", "ch_persistent_diarrhoea"),
 ("hbyc", "bachcha bahut sust hai, uth nahi raha", "ch_lethargic_unconscious"),
]

NEG = [  # (visit_type, sentence, sign that must NOT be present)
 ("anc", "khoon nahi aaya", "anc_vaginal_bleeding"),
 ("anc", "खून नहीं आया", "anc_vaginal_bleeding"),
 ("anc", "bachcha theek se hil raha hai", "anc_reduced_fetal_movement"),
 ("anc", "बुखार नहीं है", "anc_high_fever"),
 ("hbnc", "doodh achhe se pee raha hai", "nb_poor_feeding"),
 ("hbnc", "बच्चा अच्छे से दूध पी रहा है", "nb_poor_feeding"),
 ("hbnc", "jhatke nahi aaye", "nb_convulsions"),
 ("hbnc", "baby ko bukhaar nahi hai", "nb_fever"),
 ("hbnc", "बच्चे को बुखार नहीं है", "nb_fever"),
 ("hbnc", "saans theek hai", "nb_fast_breathing"),
 ("hbyc", "ulti nahi ho rahi", "ch_vomits_everything"),
]



def present(visit_type: str, text: str) -> set[str]:
    d = DangerChecker(visit_type, ("hi", "en"))
    d.add_utterance(text, "hi-IN")
    return set(d.present())


@pytest.mark.parametrize("visit_type, text, sign", POS)
def test_danger_sentence_is_caught(visit_type, text, sign):
    assert sign in present(visit_type, text)


@pytest.mark.parametrize("visit_type, text, sign", NEG)
def test_denial_is_not_an_alert(visit_type, text, sign):
    assert sign not in present(visit_type, text)


@pytest.mark.parametrize("text, want, not_want", [
    ("baby ko bukhaar hai", "nb_fever", "pnc_fever"),
    ("बच्चे को बुखार है", "nb_fever", "pnc_fever"),
    ("maa ko bukhaar hai", "pnc_fever", "nb_fever"),
    ("baby bilkul thanda hai", "nb_hypothermia", "pnc_foul_lochia"),
])
def test_hbnc_sign_goes_to_whoever_the_sentence_is_about(text, want, not_want):
    got = present("hbnc", text)
    assert want in got and not_want not in got


def test_baby_and_mother_signs_in_one_sentence_both_count():
    got = present("hbnc", "baby ko bukhaar hai aur maa ko bahut zyada khoon ja raha hai")
    assert {"nb_fever", "pnc_heavy_bleeding"} <= got
