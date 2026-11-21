# 01 — Danger signs ASHAs refer, and how people say them

Research for the ASHA voice visit-record assistant (Karnataka; Kannada/Hindi/English code-mix).
Scope: what the official sources tell ASHAs to refer, with thresholds, and the phrases people use for them.
**The app must never diagnose, treat or give doses.** Several official sources pair a sign with ASHA-level treatment (paracetamol, amoxicillin, cotrimoxazole, ORS/zinc). Those treatment steps are deliberately left out below. Every sign maps to "refer to PHC" (or "refer immediately").

Researched 13 Nov 2026. All page numbers were checked against the downloaded PDFs. "p." is the printed page number and "pdf p." is the PDF page index.

---

## Summary

- **Signs found: 73 referable signs.** Pregnancy and labour: 17. Mother after delivery: 17. Newborn 0–28 days: 24. Child 2–59 months: 15. Every one cites an official MoHFW/NHSRC source, plus F-IMNCI for the young-infant thresholds.
- **Best primary sources.** The newest is the **Integrated Training Module for ASHA 2026, Part B (MoHFW/NHSRC, uploaded Oct 2026)**. It folds HBNC and HBYC into "SSBSK" and has the fullest lists. Next come **ASHA Module 6 and Module 7 "Skills that Save Lives"** in English and Hindi, the **HBNC/HBYC Handbook for ASHA Facilitators & ANM/MPW** (with the HBNC home-visit form thresholds), the **MCP Card** and the **F-IMNCI chart booklet**.
- **The official sources disagree on key thresholds.** Newborn fever is >99 °F (37.2 °C) in Module 6 and the HBNC form but ≥37.5 °C in IMNCI. Newborn hypothermia is <35.5 °C in IMNCI and Module 6 but <35 °C (95 °F) in the 2026 module. Postpartum bleeding is ">5 pads/day" in Module 6 and the HBNC form but "2–3 pads in 20–30 min" in the 2026 module. Persistent child fever is ">7 days" in Module 7 but ">2 days" in the 2026 module. **Recommendation: for each pair, trigger on the more sensitive (lower) threshold.**
- **Kannada is the biggest gap.** No official Kannada ASHA module, MCP card or HBNC leaflet could be reached; the Karnataka and UNICEF IEC sites were unreachable or JS-only. Every Kannada phrase below is **UNSOURCED-linguistic** and must be checked by native speakers or Karnataka ASHAs before demo. Hindi terms are partly sourced from the official Hindi Module 6 and Module 7.
- **Negation is a two-way trap.** Many danger signs are negative phrases themselves: "bachcha hil nahi raha", "haalu kudithilla", "peshab nahi hua". A generic "nahi/illa → negated" rule would *suppress* real danger signs. Polarity has to be modelled per sign (see the lexicon notes and the Risks section).

---

## Topic 1 — Danger signs (YAML)

Source codes (full citations are in the Sources section):
`INT26` Integrated ASHA Module 2026 Part B · `M6` ASHA Module 6 (English) · `M6HI` Module 6 (Hindi) · `M7` ASHA Module 7 (English) · `M7HI` Module 7 (Hindi) · `HBNCH` HBNC/HBYC Handbook for AF & ANM/MPW · `MCP` MCP Card · `FIMNCI` F-IMNCI Chart Booklet.

Urgency vocabulary:
- `refer_immediately`: the source says immediate, urgent, at once or emergency.
- `refer_same_day`: the source says same day.
- `refer`: the source says refer, contact or report, with no time stated.
- `refer_if_persists`: the source refers only after a time window or failed home care.

```yaml
danger_signs:
  # ───────────── a) PREGNANT WOMAN (antenatal + labour) ─────────────
  - id: anc_vaginal_bleeding
    group: pregnancy
    official_wording: "Bleeding from vagina" (M6); "Bleeding during pregnancy" (MCP); "Bleeding from vagina" (INT26)
    threshold: "any amount (bright red bleeding or clots or tissue)" (M6)
    urgency: refer_immediately
    source: "M6; MCP; INT26"
    page: "M6 p.30 (pdf p.32) 'Health problems during pregnancy that need immediate referral'; MCP pdf p.4; INT26 p.183 item 3, also p.177 (early pregnancy)"
  - id: anc_reduced_fetal_movement
    group: pregnancy
    official_wording: "Loss of foetal movement" (M6); "Decreased foetal movements" (INT26); "Decreased/absent foetal movements is an emergency" (INT26)
    threshold: "Movements usually felt from 18–20 weeks; monitoring especially important after 24–28 weeks. Reassuring = 3 or more movements in 1 hour after meals, or 10 movements in 12 hours (DFMR). Fewer than that, or absent = refer." (INT26). M6 has no number ('Absence of movement/kicking').
    urgency: refer_immediately
    source: "INT26; M6"
    page: "INT26 p.178–179 (pdf p.188–189) and p.183 item 13; M6 p.30"
  - id: anc_severe_headache_blurred_vision
    group: pregnancy
    official_wording: "Headache/dizziness/blurred vision" (M6); "Severe headache / blurring of vision" (INT26); "Headache, blurring of vision, fits and swelling all over the body" (MCP)
    threshold: "severe headache with blurred vision or spots before the eyes" (M6)
    urgency: refer_immediately
    source: "M6; INT26; MCP"
    page: "M6 p.30; INT26 p.183 item 6; MCP pdf p.4"
  - id: anc_swelling_face_hands
    group: pregnancy
    official_wording: "Swollen face/hands" (M6); "Swelling over face / hands / body" (INT26)
    threshold: "pitting oedema over back of palm" (M6). Ankle-only swelling is NOT listed as a danger sign.
    urgency: refer_immediately
    source: "M6; INT26; MCP"
    page: "M6 p.31; INT26 p.183 item 7; MCP pdf p.4"
  - id: anc_convulsions
    group: pregnancy
    official_wording: "Convulsions/fits" (M6); "Convulsions" (INT26)
    threshold: "eyes roll, face and limbs twitch, body gets stiff and shakes, fists clenched" (M6)
    urgency: refer_immediately
    source: "M6; INT26; MCP"
    page: "M6 p.31; INT26 p.183 item 9 and p.177; MCP pdf p.4"
  - id: anc_high_fever
    group: pregnancy
    official_wording: "High grade fever" (INT26); "High fever during pregnancy or within one month of delivery" (MCP); "Fever" (M6)
    threshold: "M6: temp >100 °F (37.8 °C). INT26/MCP: no number ('high grade')."
    urgency: refer_immediately
    urgency_conflict: "M6 p.32 lists fever under NON-emergency (home care first, refer to PHC if no relief after 48 h). INT26 and MCP list it as a danger sign for immediate referral. App: flag and refer; never suggest medicine."
    source: "INT26; MCP; M6"
    page: "INT26 p.183 item 1; MCP pdf p.4; M6 p.32"
  - id: anc_severe_abdominal_pain
    group: pregnancy
    official_wording: "Severe pain abdomen / continuous pain abdomen" (INT26)
    threshold: "severe or continuous" (no number)
    urgency: refer_immediately
    source: "INT26; M6"
    page: "INT26 p.183 item 5, p.177; M6 p.30 (with loss of foetal movement)"
  - id: anc_breathlessness
    group: pregnancy
    official_wording: "Breathlessness" (INT26); "Severe Anemia with or without breathlessness" (MCP)
    threshold: none stated
    urgency: refer_immediately
    source: "INT26; MCP"
    page: "INT26 p.183 item 8; MCP pdf p.4"
  - id: anc_severe_anaemia
    group: pregnancy
    official_wording: "Severe anaemia" — "Tongue very pale, weakness, general swelling in body" (M6); "Severe Anemia" (MCP)
    threshold: "Hb cut-off for severe anaemia: UNVERIFIED in the fetched sources (often cited as <7 g/dL; do not hard-code without checking Anaemia Mukta Bharat guidelines)"
    urgency: refer
    urgency_conflict: "M6 p.31: 'Non-Emergency referral — refer to PHC/Dist. Hospital'. MCP pdf p.4 lists it with 'take to hospital immediately'."
    source: "M6; MCP"
    page: "M6 p.31; MCP pdf p.4"
  - id: anc_water_break_no_labour
    group: pregnancy
    official_wording: "Bursting of water bag without labour pains" (MCP); "Breaking of water much before due date and without any pain" (INT26); "Water breaks but labour does not start within 24 hours" (M6)
    threshold: "M6: no labour within 24 h of water breaking. MCP/INT26: any leak without pains."
    urgency: refer_immediately
    source: "MCP; INT26; M6"
    page: "MCP pdf p.4; INT26 p.183 item 12; M6 p.33 'Danger signs in labour and delivery'"
  - id: anc_preterm_labour
    group: pregnancy
    official_wording: "Labor pains before the due date" (INT26)
    threshold: "before due date (no week cut-off stated)"
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.183 item 11"
  - id: anc_prolonged_labour
    group: pregnancy
    official_wording: "Labour pain for more than 12 hours" (MCP); "Prolonged labour" (M6)
    threshold: "> 12 hours (MCP). M6: woman pushing > 12 h, or > 8 h if she has had children before, baby not coming out."
    urgency: refer_immediately
    source: "MCP; M6"
    page: "MCP pdf p.4; M6 p.33"
  - id: anc_foul_vaginal_discharge
    group: pregnancy
    official_wording: "Foul smelling discharge from vagina" (INT26)
    threshold: none
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.183 item 4"
  - id: anc_burning_urination
    group: pregnancy
    official_wording: "Burning sensation and pain while passing urine" (INT26); "Pain/burning when urinating" (M6)
    threshold: "M6: refer to PHC if no relief after 24 h"
    urgency: refer
    urgency_conflict: "INT26 puts it in the 'danger signs... immediate referral' list. M6 p.32 calls it non-emergency (refer after 24 h)."
    source: "INT26; M6"
    page: "INT26 p.183 item 2; M6 p.32"
  - id: anc_high_bp
    group: pregnancy
    official_wording: "High Blood Pressure" (INT26)
    threshold: "BP more than 140/90 mm Hg around or after 20 weeks" (INT26 p.181). Only applies when a measured value is spoken.
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.183 item 10; definition p.181"
  - id: anc_labour_green_liquor
    group: pregnancy (labour)
    official_wording: "Colour of water – green or brown" (M6)
    threshold: none
    urgency: refer_immediately
    source: M6
    page: "M6 p.33 'Danger signs in labour and delivery'"
  - id: anc_retained_placenta
    group: pregnancy (labour)
    official_wording: "Retained placenta" (M6)
    threshold: "UNVERIFIED (no time cut-off given in M6)"
    urgency: refer_immediately
    source: M6
    page: "M6 p.33"

  # ───────────── b) WOMAN AFTER DELIVERY (postnatal, to 42 days) ─────────────
  - id: pnc_heavy_bleeding
    group: postnatal
    official_wording: "Excessive bleeding" (M6, INT26); "Excessive bleeding during delivery or after delivery" (MCP)
    threshold: "M6/INT26 Table 1/HBNCH form: using > 5 pads a day, or > 1 thick cloth a day. INT26 p.48: soaking > 2–3 pads in 20–30 minutes after delivery. INT26 p.11: also large clots, or a return to heavy red bleeding after it had reduced."
    urgency: refer_immediately
    note: "M6: 'Referral is most urgent. Even the delay of a few minutes can make a difference.'"
    source: "M6; INT26; HBNCH; MCP"
    page: "M6 p.39 (pdf p.41); INT26 p.11, p.47 Table 1 row 1, p.48 item 1; HBNCH p.20 Annex 1c A3; MCP pdf p.4"
  - id: pnc_foul_lochia
    group: postnatal
    official_wording: "Puerperal sepsis (infections) – fever, foul smelling discharge, pain lower abdomen" (INT26); "Foul-smelling lochia" (INT26)
    threshold: "HBNCH form: foul-smelling discharge AND fever > 100 °F (37.8 °C) → refer"
    urgency: refer_same_day
    urgency_conflict: "M6 p.39: 'Referral on the same day is advisable'. INT26 p.11–12: foul-smelling discharge 'should be taken to a health facility immediately'."
    source: "M6; INT26; HBNCH"
    page: "M6 p.39; INT26 p.11, p.47 row 2, p.49 item 15; HBNCH p.20 Annex 1c B2"
  - id: pnc_fever
    group: postnatal
    official_wording: "Fever" (INT26); "High fever ... within one month of delivery" (MCP)
    threshold: "HBNCH form: mother's temperature > 102 °F (38.9 °C) → refer to hospital. Below that, the form has ASHA give a medicine; the APP MUST NOT. INT26/MCP give no number."
    urgency: refer_immediately
    source: "MCP; INT26; HBNCH"
    page: "MCP pdf p.4; INT26 p.49 item 6; HBNCH p.20 Annex 1c B1"
  - id: pnc_convulsions_unconscious
    group: postnatal
    official_wording: "Convulsions with or without swelling of face and hands, severe headache, and blurred vision" (M6); "Unconscious/Fits" (HBNCH)
    threshold: none
    urgency: refer_immediately
    source: "M6; INT26; HBNCH"
    page: "M6 p.39 item 3; INT26 p.48 Table 1 row 3, p.49 item 5; HBNCH p.18 Annex 1b Q5b"
  - id: pnc_headache_blurred_vision
    group: postnatal
    official_wording: "severe headache, and blurred vision" (M6); pre-eclampsia signs "can appear in post natal period also" (INT26)
    threshold: none
    urgency: refer_immediately
    source: "M6; INT26"
    page: "M6 p.39; INT26 p.182"
  - id: pnc_swelling_face_hands
    group: postnatal
    official_wording: "Swelling on face, hands and legs" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.49 item 14"
  - id: pnc_breathing_difficulty
    group: postnatal
    official_wording: "Difficulty in breathing" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.48 item 11; p.13 ('very weak, dizzy, breathless')"
  - id: pnc_severe_abdominal_pain
    group: postnatal
    official_wording: "Severe abdominal pain" (INT26); "soft or poorly contracted uterus, increasing abdominal pain" (INT26)
    threshold: none
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.12, p.48 item 10"
  - id: pnc_no_urine
    group: postnatal
    official_wording: "No urine passed within 6 hours after delivery"; "Very little or no urine output" (INT26)
    threshold: "no urine within 6 h of delivery"
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.13 'Danger Signs – Refer Immediately'; p.48 item 12"
  - id: pnc_urinary_burning_leg_swelling
    group: postnatal
    official_wording: "Urinary burning along with pain and swelling in lower limbs" (INT26); "Fever along with urinary complaints"; "Severe pain or burning while passing urine" (INT26)
    threshold: none
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.13; p.48 item 9"
  - id: pnc_pallor_weakness
    group: postnatal
    official_wording: "Pale skin or eyes, giddiness or weakness" (INT26); "Anaemia" (M6)
    threshold: "Hb threshold UNVERIFIED"
    urgency: refer
    source: "INT26; M6"
    page: "INT26 p.48 item 3, p.47 row 4; M6 p.39 item 4"
  - id: pnc_jaundice
    group: postnatal
    official_wording: "Yellowness of urine, skin or eyes" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.48 item 2"
  - id: pnc_abnormal_behaviour_harm_thoughts
    group: postnatal
    official_wording: "Abnormal behaviour such as confusion, severe behavioural change, hallucinations ... – urgent assessment/referral" (INT26); "persistently sad ... thoughts of harming herself or the baby" (INT26); "Is mother speaking abnormally" (HBNCH)
    threshold: "Mood changes in the first days are normal. Refer if severe, persisting beyond about a week (M6), or any harm thoughts."
    urgency: refer_immediately
    source: "INT26; HBNCH; M6"
    page: "INT26 p.13, p.49 item 13; HBNCH p.20 Annex 1c B3; M6 p.40 item 7"
  - id: pnc_breast_problem_fever
    group: postnatal
    official_wording: "Cracked and painful nipples" (INT26); engorged breasts "If the mother has fever then, refer to a hospital" (HBNCH)
    threshold: "refer if breast problem + fever, or red/shiny nipple condition persists"
    urgency: refer
    source: "HBNCH; INT26"
    page: "HBNCH p.21 Annex 1c B5; INT26 p.48 item 4"
  - id: pnc_perineal_infection
    group: postnatal
    official_wording: "Perineal swelling and infection" — pain, swelling and discharge from the stitch line, with or without fever (INT26)
    threshold: "M6: refer to PHC/CHC if there is fever"
    urgency: refer
    source: "INT26; M6"
    page: "INT26 p.48 Table 1 row 5; M6 p.40 item 6"
  - id: pnc_not_eating_vomiting
    group: postnatal
    official_wording: "No appetite or inability to eat for more than 24 hours"; "Repeated vomiting"; "Severe weakness or dizziness" (INT26)
    threshold: "> 24 h not eating"
    urgency: refer
    source: INT26
    page: "INT26 p.12–13 ('Danger signs')"
  - id: pnc_stool_incontinence
    group: postnatal
    official_wording: "Incontinence of stool" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.49 item 8"

  # ───────────── c) NEWBORN 0–28 DAYS ─────────────
  - id: nb_fast_breathing
    group: newborn
    official_wording: "Fast breathing (more than 60 breaths / min)" (INT26); "Respiratory rate more than 60 per minute" (HBNCH); "Fast breathing (60 breaths per minute or more)" (FIMNCI)
    threshold: "INT26/HBNCH: > 60/min. FIMNCI/INT26 p.126: ≥ 60/min. Count for a full minute with the baby calm. Normal is 40–60 (INT26 p.8)."
    urgency: refer_immediately
    source: "INT26; HBNCH; FIMNCI"
    page: "INT26 p.8, p.46, p.126; HBNCH p.23 Annex 1c E7; FIMNCI pdf p.3 (chart p.1)"
  - id: nb_chest_indrawing
    group: newborn
    official_wording: "Severe chest in-drawing" (INT26, FIMNCI); "Has chest indrawing" (M7); "Difficulty in breathing, indrawing of chest" (INT26)
    threshold: "visible lower-chest indrawing"
    urgency: refer_immediately
    source: "INT26; M7; HBNCH; FIMNCI"
    page: "INT26 p.8, p.46; M7 p.55; HBNCH p.23 E6; FIMNCI chart p.1"
  - id: nb_grunting_nasal_flaring
    group: newborn
    official_wording: "Grunting sound while breathing"; "Nasal flaring" (INT26, FIMNCI)
    threshold: none
    urgency: refer_immediately
    note: "INT26 marks these 'Not in SSBSK but in IMNCI'"
    source: "INT26; FIMNCI"
    page: "INT26 p.8; FIMNCI chart p.1"
  - id: nb_cyanosis
    group: newborn
    official_wording: "Bluish colour of lips, tongue, or face" (INT26)
    threshold: none
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.8; p.29 (hypothermia: 'pale or bluish')"
  - id: nb_apnoea_slow_breathing
    group: newborn
    official_wording: "Slow or irregular breathing"; "Pauses in breathing lasting more than 20 seconds" (INT26)
    threshold: "pause > 20 s"
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.8"
  - id: nb_fever
    group: newborn
    official_wording: "Has fever" (M7, MCP); "fever with a temperature > 99 °F (37.2 °C)" (HBNCH); "axillary temperature 37.5 °C or above (or feels hot to touch)" (FIMNCI)
    threshold: "CONFLICT. M6 p.60, HBNCH p.22, INT26 p.28: > 99 °F (37.2 °C). INT26 p.8 says normal is 97.7–99.5 °F (36.5–37.5 °C). FIMNCI: ≥ 37.5 °C. M6: if overdressed or in a hot room, unwrap and recheck after 30 min; refer if still high."
    urgency: refer_immediately
    source: "M6; HBNCH; INT26; FIMNCI; M7; MCP"
    page: "M6 p.60 (pdf p.62); HBNCH p.22 C3 and p.23 E5; INT26 p.8, p.28, p.46; FIMNCI chart p.1; M7 p.55; MCP pdf p.28"
  - id: nb_hypothermia
    group: newborn
    official_wording: "Is cold to touch" (M7, MCP); "Mother says the baby is 'cold to touch'" (HBNCH)
    threshold: "CONFLICT. FIMNCI: < 35.5 °C → refer urgently; 35.5–36.4 °C → warm and reassess in 1 h, refer if no improvement. M6 p.59: < 97 °F (36.1 °C) cold, < 95.9 °F (35.5 °C) too cold; refer if not stable within 4 h. INT26 p.28–29: < 95 °F (35 °C) = danger signs of hypothermia, refer immediately. M7 p.56: refer if < 95 °F persists after re-warming for 24 h."
    urgency: refer_immediately
    source: "FIMNCI; M6; INT26; M7; HBNCH; MCP"
    page: "FIMNCI chart p.1; M6 p.59 (pdf p.61); INT26 p.28–29; M7 p.56; HBNCH p.22 C3, p.23 E5; MCP pdf p.28"
  - id: nb_poor_feeding
    group: newborn
    official_wording: "Stops feeding" (M7); "Is sucking weakly or refuses to breast feed" (MCP); "Feeding less/stopped" (HBNCH); "Inability to suck milk" (INT26)
    threshold: "Normal is 8–10+ feeds per 24 h (INT26 p.8). HBNCH day-1 check: fed weakly / spoon only / not at all."
    urgency: refer_immediately
    source: "M7; MCP; HBNCH; INT26"
    page: "M7 p.55; MCP pdf p.28; HBNCH p.18 Q8, p.19 Q5b, p.23 E2; INT26 p.46"
  - id: nb_lethargy_limp
    group: newborn
    official_wording: "Limbs become limp" (M7); "Is lethargic or unconscious" (MCP); "Lethargic or unconscious or less than normal movements" (FIMNCI); "Dull and lethargic baby" (INT26)
    threshold: none
    urgency: refer_immediately
    source: "M7; MCP; FIMNCI; INT26; HBNCH"
    page: "M7 p.55; MCP pdf p.28; FIMNCI chart p.1; INT26 p.46; HBNCH p.23 E1"
  - id: nb_weak_cry
    group: newborn
    official_wording: "Cry weak / stopped" (HBNCH); "Is unable to cry" (MCP)
    threshold: none
    urgency: refer_immediately
    source: "HBNCH; MCP; INT26"
    page: "HBNCH p.19 Q5c, p.23 E3; MCP pdf p.28; INT26 p.29"
  - id: nb_convulsions
    group: newborn
    official_wording: "Convulsions" (M7, FIMNCI, MCP); "Seizures" (INT26)
    threshold: none
    urgency: refer_immediately
    source: "M7; INT26; MCP; FIMNCI"
    page: "M7 p.56; INT26 p.46; MCP pdf p.28; FIMNCI chart p.1"
  - id: nb_jaundice_severe
    group: newborn
    official_wording: "Has yellow palms and soles" (MCP); "Becomes yellow (jaundice) on first day or jaundice persists after 14 days" (M7); "Palms and soles yellow or age < 24 hours or age 14 days or more" = SEVERE JAUNDICE (FIMNCI)
    threshold: "yellow palms or soles; OR any jaundice in the first 24 h; OR jaundice lasting ≥ 14 days"
    urgency: refer_immediately
    source: "FIMNCI; M7; MCP; INT26; HBNCH"
    page: "FIMNCI chart p.1; M7 p.56; MCP pdf p.28; INT26 p.46; HBNCH p.22 C4"
  - id: nb_blood_in_stool
    group: newborn
    official_wording: "Has blood in stool(s)" (MCP, INT26)
    threshold: none
    urgency: refer_immediately
    source: "MCP; INT26"
    page: "MCP pdf p.28; INT26 p.46"
  - id: nb_bleeding_any_site
    group: newborn
    official_wording: "Bleeding from nose, mouth or anus" (M7); "Is umbilical cord bleeding" (HBNCH)
    threshold: none
    urgency: refer_immediately
    source: "M7; HBNCH"
    page: "M7 p.56; HBNCH p.19 Part II Q3"
  - id: nb_umbilical_infection
    group: newborn
    official_wording: "Umbilical cord is swollen, red or has pus discharge" (INT26); "Pus on umbilicus" (HBNCH)
    threshold: none
    urgency: refer
    urgency_conflict: "FIMNCI classifies 'umbilicus red or draining pus' alone as LOCAL BACTERIAL INFECTION (home treatment, follow-up in 2 days), not urgent referral. HBNCH lists it as a sepsis sign (refer immediately). INT26 says report immediately to CHO/MPW."
    source: "INT26; HBNCH; FIMNCI"
    page: "INT26 p.8, p.46; HBNCH p.23 E8; FIMNCI chart p.1"
  - id: nb_skin_pustules
    group: newborn
    official_wording: "More than 10 pustules over body or one large boil" (INT26); "10 or more skin pustules or a big boil" (FIMNCI)
    threshold: "≥ 10 pustules (FIMNCI) or > 10 (INT26), or one big boil"
    urgency: refer_immediately
    source: "INT26; FIMNCI"
    page: "INT26 p.46; FIMNCI chart p.1"
  - id: nb_no_urine_stool
    group: newborn
    official_wording: "Inability to pass stools and urine" (INT26)
    threshold: "Normal: urine within 24 h, meconium within 24–48 h, urine 6–8 times/day (INT26 p.8). HBNCH: urine < 6 times/day → feeding advice."
    urgency: refer
    source: "INT26; HBNCH"
    page: "INT26 p.8, p.46; HBNCH p.20 A6"
  - id: nb_abdominal_distension_vomiting
    group: newborn
    official_wording: "Distended abdomen or mother says baby vomits often" (HBNCH)
    threshold: none
    urgency: refer_immediately
    source: HBNCH
    page: "HBNCH p.23 Annex 1c E4 (sepsis sign)"
  - id: nb_diarrhoea
    group: newborn
    official_wording: "Diarrhoea" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.46"
  - id: nb_eye_discharge
    group: newborn
    official_wording: "Eyes are red and infected" (INT26); "Are the eyes swollen or with pus" (HBNCH)
    threshold: none
    urgency: refer
    source: "INT26; HBNCH"
    page: "INT26 p.46–47; HBNCH p.21 C1"
  - id: nb_very_low_birth_weight
    group: newborn
    official_wording: "If the weight is less than 1.8 kg then refer the baby to Sick New born care unit" (HBNCH); baby "not gaining weight → refer to SNCU" (HBNCH)
    threshold: "< 1.8 kg → refer; < 2.5 kg = LBW needing extra care and visits"
    urgency: refer
    source: HBNCH
    page: "HBNCH p.21 Annex 1c C2"
  - id: nb_tetanus_stiffness
    group: newborn
    official_wording: "Tetanus (stiffness after the fourth day), unable to suckle or open mouth" (M7)
    threshold: "after day 4"
    urgency: refer_immediately
    source: M7
    page: "M7 p.56"
  - id: nb_bulging_fontanelle
    group: newborn
    official_wording: "Bulging fontanelle" (FIMNCI)
    threshold: none
    urgency: refer_immediately
    source: FIMNCI
    page: "FIMNCI chart p.1"
  - id: nb_birth_asphyxia
    group: newborn
    official_wording: "no cry or a weak cry ... no breathing or weak breathing or gasping ... Asphyxia" (M6)
    threshold: "at birth / first minutes"
    urgency: refer_immediately
    note: "M7 teaches ASHA resuscitation. The app should only flag it and refer."
    source: "M6; M7"
    page: "M6 p.44 step 5; M7 Part C asphyxia section (page not re-checked: UNVERIFIED)"

  # ───────────── d) CHILD 2 MONTHS – 5 YEARS ─────────────
  - id: ch_unable_to_drink
    group: child_u5
    official_wording: "Not able to drink or breastfeed" (M7, INT26)
    threshold: "cannot suck or swallow when offered"
    urgency: refer_immediately
    source: "M7; INT26; FIMNCI"
    page: "M7 p.20 (pdf p.22); INT26 p.123, p.126"
  - id: ch_vomits_everything
    group: child_u5
    official_wording: "Vomits everything" (M7); "Persistent vomiting" (INT26)
    threshold: "cannot keep anything down"
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.20; INT26 p.123, p.126"
  - id: ch_convulsions
    group: child_u5
    official_wording: "Has convulsions" (M7); "Convulsions/fits" (INT26)
    threshold: none
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.20; INT26 p.123–124, p.126"
  - id: ch_lethargic_unconscious
    group: child_u5
    official_wording: "Is lethargic or unconscious" (M7)
    threshold: none
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.20; INT26 p.123"
  - id: ch_chest_indrawing
    group: child_u5
    official_wording: "A child with any chest indrawing should be referred to the hospital" (M7)
    threshold: none
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.29; INT26 p.123"
  - id: ch_fast_breathing
    group: child_u5
    official_wording: "Fast breathing" (M7, INT26); "rapid and/or difficult breathing" (MCP)
    threshold: "2–12 months: ≥ 50/min; 12 months–5 years: ≥ 40/min (exactly 12 months uses 40)"
    urgency: refer
    note: "Official modules classify fast breathing alone (no danger sign, no chest indrawing) as PNEUMONIA with ASHA-level antibiotic. The app must not suggest treatment, so it flags 'refer to PHC'."
    source: "M7; INT26; MCP"
    page: "M7 p.29 (pdf p.31); INT26 p.123, p.126; MCP pdf p.25"
  - id: ch_fever_persistent
    group: child_u5
    official_wording: "fever has been present every day for more than seven days" (M7); "fever ... present every day for more than two days" (INT26); "If the child has high fever take her/him to the health centre" (MCP)
    threshold: "Fever = axillary ≥ 37.5 °C / 99.5 °F (INT26 p.124). Duration: > 7 days (M7) vs > 2 days (INT26): CONFLICT. M7: cough with fever > 3 days → refer."
    urgency: refer_immediately
    source: "INT26; M7; MCP"
    page: "INT26 p.124; M7 p.22 (pdf p.24), p.29; MCP pdf p.25"
  - id: ch_stiff_neck
    group: child_u5
    official_wording: "Stiff neck" (M7, INT26)
    threshold: none
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.22; INT26 p.124"
  - id: ch_severe_dehydration
    group: child_u5
    official_wording: "Severe Dehydration" — two of: lethargic or unconscious; sunken eyes; not able to drink or drinking poorly; skin pinch goes back very slowly (M7)
    threshold: "any 2 of the 4 signs"
    urgency: refer_immediately
    source: "M7; INT26"
    page: "M7 p.25 (pdf p.27); INT26 p.124"
  - id: ch_persistent_diarrhoea
    group: child_u5
    official_wording: "Diarrhoea for 14 days or more" (M7)
    threshold: "≥ 14 days"
    urgency: refer
    source: M7
    page: "M7 p.25"
  - id: ch_blood_in_stool
    group: child_u5
    official_wording: "Blood in the stool" = Dysentery (M7)
    threshold: none
    urgency: refer
    note: "M7: 'Referral if possible' or ASHA-level antibiotic. App: refer."
    source: "M7; INT26"
    page: "M7 p.25; INT26 p.123"
  - id: ch_chronic_cough
    group: child_u5
    official_wording: "cough, even if mild, for more than 30 days" (M7)
    threshold: "> 30 days; or cough + fever > 3 days"
    urgency: refer
    source: M7
    page: "M7 p.29"
  - id: ch_severe_acute_malnutrition
    group: child_u5
    official_wording: "Oedema of both feet"; "Weight for Age/Length < -3 SD (red color on MCP card)" (INT26); "visible severe wasting ... urgent treatment and referral" (M7)
    threshold: "< -3 SD / red zone on the MCP growth chart; bilateral pedal oedema"
    urgency: refer_immediately
    source: "INT26; M7; MCP"
    page: "INT26 p.124; M7 Part A nutrition (pdf p.~14, page not re-checked: UNVERIFIED); MCP growth chart pdf p.24–25 ('Very Dangerous — Talk to the AWW/ANM immediately')"
  - id: ch_severe_pallor
    group: child_u5
    official_wording: "Severe palmar pallor" (INT26)
    threshold: none
    urgency: refer
    source: INT26
    page: "INT26 p.124"
  - id: ch_aefi_serious
    group: child_u5
    official_wording: "Refer immediately ... High fever; Convulsions; Excessive crying; Swelling of face or difficulty in breathing; Baby becomes pale and limp" (INT26, AEFI)
    threshold: "after any vaccination"
    urgency: refer_immediately
    source: INT26
    page: "INT26 p.102 (pdf p.112)"
```

Extra, not in the four groups: **post-abortion danger signs**. These are heavy bleeding, high fever, severe abdominal pain, fainting/confusion and foul-smelling vaginal discharge, all for immediate referral (M7 p.37). INT26 p.197 adds "No periods even after 6 weeks". Add `pa_*` ids if the app will record post-abortion visits.

---

## Topic 2 — Lexicon (YAML)

How to read this:
- Each phrase is `"script | romanised | provenance"`.
- Provenance tags:
  - `OFFICIAL-M6HI p.N` / `OFFICIAL-M7HI p.N`: wording printed in the official Hindi ASHA module, on that printed page.
  - `UNSOURCED-linguistic`: from general language knowledge. **Must be checked with native speakers or ASHAs.**
- **No Kannada phrase could be sourced.** All `kn` entries are UNSOURCED-linguistic and written in colloquial Bengaluru/Old-Mysore register. North Karnataka (Dharwad/Kalaburagi) speech differs.
- `negations` are phrases meaning the sign is ABSENT or resolved. A ⚠ marks signs whose danger phrase itself contains a negator (nahi/illa). For those, "nahi/illa" means danger, and the negations list holds the *positive* (normal) phrasing.

Global patterns, for the classifier rather than per sign:
- **Hindi negators:** नहीं/nahi/nahin, ना/na, कोई … नहीं/koi … nahi, अब नहीं/ab nahi (resolved), बंद हो गया/band ho gaya (stopped: polarity depends on the sign), ठीक है/theek hai.
- **Kannada negators:** ಇಲ್ಲ/illa, -ಲ್ಲ (-lla: aagilla, bandilla, kudithilla), ಏನೂ ಇಲ್ಲ/enu illa, ಈಗ ಇಲ್ಲ/iga illa, ನಿಂತಿದೆ/nintide (stopped: polarity depends on the sign), ಸರಿ ಇದೆ/sari ide.
- **Hedges that must NOT negate:** "thoda thoda", "kabhi kabhi", "swalpa" (ಸ್ವಲ್ಪ), "jaasti illa aadru ide" (not much, but it's there). Treat these as PRESENT.
- **Past or resolved:** "pehle tha, ab nahi" and "monne ittu, iga illa" (ಮೊನ್ನೆ ಇತ್ತು, ಈಗ ಇಲ್ಲ). Record as history and still show the ASHA, because convulsions or bleeding earlier today still warrant referral.

```yaml
lexicon:
  # ───────── PREGNANCY ─────────
  anc_vaginal_bleeding:
    hi:
      - "योनि से खून का बहना (रक्तस्राव) | yoni se khoon ka behna (raktasrav) | OFFICIAL-M6HI p.30"
      - "खून आ रहा है | khoon aa raha hai | UNSOURCED-linguistic"
      - "नीचे से खून जा रहा है | neeche se khoon ja raha hai | UNSOURCED-linguistic"
      - "कपड़े पर दाग / धब्बे लग रहे | kapde par daag / dhabbe lag rahe | UNSOURCED-linguistic"
      - "महीने जैसा खून | mahine jaisa khoon | UNSOURCED-linguistic"
    kn:
      - "ರಕ್ತಸ್ರಾವ ಆಗ್ತಿದೆ | raktasraava aagtide | UNSOURCED-linguistic"
      - "ರಕ್ತ ಹೋಗ್ತಾ ಇದೆ | rakta hogta ide | UNSOURCED-linguistic"
      - "ಕೆಳಗಡೆಯಿಂದ ರಕ್ತ ಬರ್ತಿದೆ | kelagadeyinda rakta bartide | UNSOURCED-linguistic"
      - "ಮುಟ್ಟಿನ ಹಾಗೆ ರಕ್ತ | muttina haage rakta | UNSOURCED-linguistic"
    codemix:
      - "bleeding ho rahi hai | UNSOURCED-linguistic"
      - "spotting hai thoda | UNSOURCED-linguistic"
      - "bleeding aagtide / blood bartide | UNSOURCED-linguistic"
    negations:
      - "खून नहीं आ रहा | khoon nahi aa raha"
      - "bleeding nahi hai / koi daag nahi"
      - "ರಕ್ತ ಹೋಗ್ತಿಲ್ಲ | rakta hogtilla"
      - "bleeding illa"
      - "NOTE: 'bleeding band ho gaya' / 'rakta nintide' = stopped → still record and refer if it happened in pregnancy"

  anc_reduced_fetal_movement:   # ⚠ danger phrase contains a negator
    hi:
      - "भ्रूण का हिलना-डुलना बंद हो जाना | bhroon ka hilna-dulna band ho jana | OFFICIAL-M6HI p.30"
      - "हाथ-पैर मारना बंद कर दे | haath-pair maarna band kar de | OFFICIAL-M6HI p.30"
      - "बच्चा पेट में हिल नहीं रहा | bachcha pet mein hil nahi raha | UNSOURCED-linguistic"
      - "बच्चा लात नहीं मार रहा | bachcha laat nahi maar raha | UNSOURCED-linguistic"
      - "कल से हलचल कम है | kal se halchal kam hai | UNSOURCED-linguistic"
    kn:
      - "ಹೊಟ್ಟೆಯಲ್ಲಿ ಮಗು ಅಲ್ಲಾಡ್ತಿಲ್ಲ | hotteyalli magu allaadtilla | UNSOURCED-linguistic"
      - "ಮಗು ಒದೀತಿಲ್ಲ | magu odeetilla | UNSOURCED-linguistic"
      - "ಮಗುವಿನ ಚಲನೆ ಕಡಿಮೆ ಆಗಿದೆ | maguvina chalane kadime aagide | UNSOURCED-linguistic"
    codemix:
      - "baby movement kam hai / feel nahi ho raha | UNSOURCED-linguistic"
      - "movement kammi ide / baby move aagtilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing (sign absent)
      - "बच्चा ठीक से हिल रहा है | bachcha theek se hil raha hai"
      - "laat maar raha hai, movement normal hai"
      - "ಮಗು ಚೆನ್ನಾಗಿ ಒದೀತಿದೆ | magu chennaagi odeetide"
      - "movement chennagide"

  anc_severe_headache_blurred_vision:
    hi:
      - "सिरदर्द/ सिर चकराना/ धुंधला दिखाई देना | sirdard / sir chakrana / dhundhla dikhai dena | OFFICIAL-M6HI p.30"
      - "आँखों के आगे धब्बे दिखाई देना | aankhon ke aage dhabbe dikhai dena | OFFICIAL-M6HI p.30"
      - "सिर फटा जा रहा है | sir phata ja raha hai | UNSOURCED-linguistic"
      - "आँखों के आगे अंधेरा छा जाता है | aankhon ke aage andhera chha jata hai | UNSOURCED-linguistic"
    kn:
      - "ತಲೆ ನೋವು ತುಂಬಾ ಜಾಸ್ತಿ | tale novu tumba jaasti | UNSOURCED-linguistic"
      - "ಕಣ್ಣು ಮಂಜು ಮಂಜಾಗಿ ಕಾಣ್ತಿದೆ | kannu manju manjaagi kaantide | UNSOURCED-linguistic"
      - "ಕಣ್ಣು ಕತ್ತಲೆ ಬರ್ತಿದೆ | kannu kattale bartide | UNSOURCED-linguistic"
      - "ತಲೆ ಸುತ್ತು | tale suttu | UNSOURCED-linguistic"
    codemix:
      - "severe headache hai, vision blurry | UNSOURCED-linguistic"
      - "headache jaasti, kannu blur aagtide | UNSOURCED-linguistic"
    negations:
      - "सिर दर्द नहीं | sir dard nahi"
      - "ತಲೆ ನೋವು ಇಲ್ಲ | tale novu illa"
      - "NOTE: mild 'thoda sir dard' is not the official sign; classifier should require 'severe/bahut/tumba' or visual symptom"

  anc_swelling_face_hands:
    hi:
      - "चेहरे/हाथों में सूजन | chehre/haathon mein soojan | OFFICIAL-M6HI p.31"
      - "अंगुली से दबाने पर गड्ढे पड़ जाते हैं | anguli se dabane par gaddhe pad jaate hain | OFFICIAL-M6HI p.31"
      - "मुँह फूल गया है | munh phool gaya hai | UNSOURCED-linguistic"
    kn:
      - "ಮುಖ ಊದಿಕೊಂಡಿದೆ | mukha oodikondide | UNSOURCED-linguistic"
      - "ಕೈ ಬಾವು ಬಂದಿದೆ | kai baavu bandide | UNSOURCED-linguistic"
      - "ಒತ್ತಿದ್ರೆ ಗುಳಿ ಬೀಳುತ್ತೆ | ottidre guli beelutte | UNSOURCED-linguistic"
    codemix:
      - "face pe swelling hai | UNSOURCED-linguistic"
      - "mukha swelling aagide | UNSOURCED-linguistic"
    negations:
      - "सूजन नहीं | soojan nahi"
      - "ಬಾವು ಇಲ್ಲ | baavu illa"
      - "NOTE: 'pair mein soojan' / 'kaalu baavu' (feet only) is common late in pregnancy and is NOT the official sign; record, don't auto-flag"

  anc_convulsions:
    hi:
      - "शरीर में ऐंठन / दौरा पड़ना | shareer mein ainthan / daura padna | OFFICIAL-M6HI p.31"
      - "आँखें घूम जाना, मुट्ठी भिंच जाना | aankhen ghoom jana, mutthi bhinch jana | OFFICIAL-M6HI p.31"
      - "झटके आ रहे थे | jhatke aa rahe the | UNSOURCED-linguistic"
      - "मिर्गी जैसा दौरा | mirgi jaisa daura | UNSOURCED-linguistic"
      - "दाँत भिंच गए, बेहोश हो गई | daant bhinch gaye, behosh ho gayi | UNSOURCED-linguistic"
    kn:
      - "ಫಿಟ್ಸ್ ಬಂತು | fits bantu | UNSOURCED-linguistic"
      - "ಸೆಳವು ಬಂತು | selavu bantu | UNSOURCED-linguistic"
      - "ಕೈಕಾಲು ಎಳ್ಕೊಳ್ತಿತ್ತು | kaikaalu elkoltittu | UNSOURCED-linguistic"
      - "ಮೂರ್ಛೆ ಹೋದಳು | moorchhe hodalu (fainted — ambiguous) | UNSOURCED-linguistic"
    codemix:
      - "fits aaye / fit pada | UNSOURCED-linguistic"
      - "fits bandittu | UNSOURCED-linguistic"
    negations:
      - "कोई दौरा नहीं | koi daura nahi"
      - "fits illa / ಸೆಳವು ಇಲ್ಲ | selavu illa"

  anc_high_fever:
    hi:
      - "तेज़ बुखार | tez bukhaar | UNSOURCED-linguistic"
      - "बदन तप रहा है | badan tap raha hai | UNSOURCED-linguistic"
      - "ठंड लग के बुखार | thand lag ke bukhaar | UNSOURCED-linguistic"
    kn:
      - "ಜೋರು ಜ್ವರ | joru jvara | UNSOURCED-linguistic"
      - "ಮೈ ಸುಡ್ತಿದೆ | mai sudtide | UNSOURCED-linguistic"
      - "ಚಳಿ ಜ್ವರ | chali jvara | UNSOURCED-linguistic"
    codemix:
      - "high fever hai, 102 hai | UNSOURCED-linguistic"
      - "fever jaasti ide | UNSOURCED-linguistic"
    negations:
      - "बुखार नहीं / बुखार उतर गया | bukhaar nahi / bukhaar utar gaya"
      - "ಜ್ವರ ಇಲ್ಲ / ಜ್ವರ ಬಿಟ್ಟಿದೆ | jvara illa / jvara bittide"

  anc_severe_abdominal_pain:
    hi:
      - "पेट में बहुत तेज़ दर्द | pet mein bahut tez dard | UNSOURCED-linguistic"
      - "लगातार पेट दर्द | lagaataar pet dard | UNSOURCED-linguistic"
    kn:
      - "ಹೊಟ್ಟೆ ನೋವು ತುಂಬಾ ಜಾಸ್ತಿ | hotte novu tumba jaasti | UNSOURCED-linguistic"
      - "ಹೊಟ್ಟೆ ನೋವು ನಿಲ್ತಿಲ್ಲ | hotte novu niltilla | UNSOURCED-linguistic"
    codemix:
      - "stomach pain bahut hai | UNSOURCED-linguistic"
      - "tummy pain continuous aagide | UNSOURCED-linguistic"
    negations:
      - "पेट दर्द नहीं | pet dard nahi"
      - "ಹೊಟ್ಟೆ ನೋವು ಇಲ್ಲ | hotte novu illa"

  anc_breathlessness:
    hi:
      - "साँस फूल रही है | saans phool rahi hai | UNSOURCED-linguistic"
      - "साँस लेने में तकलीफ | saans lene mein takleef | UNSOURCED-linguistic"
    kn:
      - "ಉಸಿರು ಕಟ್ಟುತ್ತಿದೆ | usiru kattuttide | UNSOURCED-linguistic"
      - "ಏದುಸಿರು ಬರ್ತಿದೆ | edusiru bartide | UNSOURCED-linguistic"
      - "ದಮ್ಮು ಬರ್ತಿದೆ | dammu bartide | UNSOURCED-linguistic"
    codemix:
      - "breathing problem hai | UNSOURCED-linguistic"
      - "breathing kashta aagtide | UNSOURCED-linguistic"
    negations:
      - "साँस ठीक है | saans theek hai"
      - "ಉಸಿರಾಟ ಸರಿ ಇದೆ | usiraata sari ide"

  anc_severe_anaemia:
    hi:
      - "गंभीर खून की कमी | gambhir khoon ki kami | OFFICIAL-M6HI p.31"
      - "जीभ का रंग सफेद | jeebh ka rang safed | OFFICIAL-M6HI p.31"
      - "खून कम है, चक्कर आते हैं | khoon kam hai, chakkar aate hain | UNSOURCED-linguistic"
      - "पीली पड़ गई है (=pale, NOT jaundice) | peeli pad gayi hai | UNSOURCED-linguistic"
    kn:
      - "ರಕ್ತ ಕಡಿಮೆ ಇದೆ | rakta kadime ide | UNSOURCED-linguistic"
      - "ಬಿಳಿಚಿಕೊಂಡಿದ್ದಾಳೆ | bilichikondiddaale | UNSOURCED-linguistic"
      - "ನಾಲಿಗೆ ಬಿಳಿ | naalige bili | UNSOURCED-linguistic"
    codemix:
      - "HB kam hai, HB 6 hai | UNSOURCED-linguistic"
      - "HB kammi ide | UNSOURCED-linguistic"
    negations:
      - "HB theek hai / HB 11 hai"
      - "HB normal ide"

  anc_water_break_no_labour:
    hi:
      - "पानी की थैली फट गई, दर्द नहीं | paani ki thaili phat gayi, dard nahi | UNSOURCED-linguistic"
      - "नीचे से पानी जा रहा है | neeche se paani ja raha hai | UNSOURCED-linguistic"
    kn:
      - "ನೀರು ಹೋಯ್ತು, ನೋವು ಇಲ್ಲ | neeru hoytu, novu illa | UNSOURCED-linguistic"
      - "ನೀರಿನ ಚೀಲ ಒಡೆದಿದೆ | neerina cheela odedide | UNSOURCED-linguistic"
    codemix:
      - "water break ho gaya, pain nahi | UNSOURCED-linguistic"
      - "water leak aagtide | UNSOURCED-linguistic"
    negations:
      - "पानी नहीं गया | paani nahi gaya"
      - "ನೀರು ಹೋಗಿಲ್ಲ | neeru hogilla"
      - "NOTE: 'dard nahi'/'novu illa' here is part of the DANGER pattern, not a negation of the sign"

  anc_preterm_labour:
    hi:
      - "दिन पूरे होने से पहले दर्द उठ रहे हैं | din poore hone se pehle dard uth rahe hain | UNSOURCED-linguistic"
      - "सातवें महीने में ही दर्द | saatven mahine mein hi dard | UNSOURCED-linguistic"
    kn:
      - "ದಿನ ತುಂಬೋಕೆ ಮುಂಚೆನೇ ಹೆರಿಗೆ ನೋವು | dina tumboke munchene herige novu | UNSOURCED-linguistic"
    codemix:
      - "due date se pehle pain | UNSOURCED-linguistic"
      - "due date ge munche labour pain | UNSOURCED-linguistic"
    negations:
      - "दर्द नहीं है | dard nahi hai"
      - "ಹೆರಿಗೆ ನೋವು ಇಲ್ಲ | herige novu illa"

  anc_prolonged_labour:
    hi:
      - "कल रात से दर्द है, बच्चा नहीं हुआ | kal raat se dard hai, bachcha nahi hua | UNSOURCED-linguistic"
      - "बारह घंटे से ज़्यादा दर्द | baarah ghante se zyaada dard | UNSOURCED-linguistic"
    kn:
      - "ನಿನ್ನೆಯಿಂದ ಹೆರಿಗೆ ನೋವು, ಇನ್ನೂ ಆಗಿಲ್ಲ | ninneyinda herige novu, innu aagilla | UNSOURCED-linguistic"
    codemix:
      - "12 ghante se labour pain | UNSOURCED-linguistic"
      - "labour pain 12 hours inda ide | UNSOURCED-linguistic"
    negations:
      - "delivery ho gayi / ಹೆರಿಗೆ ಆಯ್ತು | herige aaytu (resolved)"

  anc_foul_vaginal_discharge:
    hi:
      - "बदबूदार सफेद पानी | badboodaar safed paani | UNSOURCED-linguistic"
      - "नीचे से बदबू आ रही | neeche se badboo aa rahi | UNSOURCED-linguistic"
    kn:
      - "ಕೆಟ್ಟ ವಾಸನೆ ಬಿಳಿ ಸೆರಗು | ketta vaasane bili seragu | UNSOURCED-linguistic"
      - "ಕೆಳಗೆ ವಾಸನೆ ಬರ್ತಿದೆ | kelage vaasane bartide | UNSOURCED-linguistic"
    codemix:
      - "smelly discharge hai | UNSOURCED-linguistic"
      - "white discharge smell ide | UNSOURCED-linguistic"
    negations:
      - "बदबू नहीं | badboo nahi"
      - "ವಾಸನೆ ಇಲ್ಲ | vaasane illa"

  anc_burning_urination:
    hi:
      - "पेशाब में जलन | peshaab mein jalan | UNSOURCED-linguistic"
      - "पेशाब करते समय दर्द | peshaab karte samay dard | UNSOURCED-linguistic"
    kn:
      - "ಉರಿ ಮೂತ್ರ | uri mootra | UNSOURCED-linguistic"
      - "ಮೂತ್ರ ಮಾಡುವಾಗ ಉರಿ | mootra maaduvaaga uri | UNSOURCED-linguistic"
    codemix:
      - "urine mein burning | UNSOURCED-linguistic"
      - "urine burning ide | UNSOURCED-linguistic"
    negations:
      - "जलन नहीं | jalan nahi"
      - "ಉರಿ ಇಲ್ಲ | uri illa"

  anc_high_bp:
    hi:
      - "बीपी बढ़ा हुआ है | BP badha hua hai | UNSOURCED-linguistic"
    kn:
      - "ಬಿಪಿ ಜಾಸ್ತಿ ಇದೆ | BP jaasti ide | UNSOURCED-linguistic"
    codemix:
      - "BP 150 by 100 | UNSOURCED-linguistic (numbers: see 02-vocab-numbers.md)"
      - "BP high ide | UNSOURCED-linguistic"
    negations:
      - "BP normal hai / BP sari ide"

  anc_labour_green_liquor:
    hi:
      - "हरा/भूरा पानी आया | hara/bhoora paani aaya | UNSOURCED-linguistic"
    kn:
      - "ಹಸಿರು ಬಣ್ಣದ ನೀರು ಹೋಯ್ತು | hasiru bannada neeru hoytu | UNSOURCED-linguistic"
    codemix:
      - "green colour paani | UNSOURCED-linguistic"
      - "green water hoytu | UNSOURCED-linguistic"
    negations:
      - "पानी साफ था | paani saaf tha"
      - "ನೀರು ಕ್ಲಿಯರ್ ಇತ್ತು | neeru clear ittu"

  anc_retained_placenta:
    hi:
      - "आँवल/ओल नहीं निकली | aanval/ol nahi nikli | UNSOURCED-linguistic (regional variants: 'phool', 'jer' — validate)"
    kn:
      - "ಮಾಸು ಬಿದ್ದಿಲ್ಲ | maasu biddilla | UNSOURCED-linguistic"
      - "ಕಸ ಬಿದ್ದಿಲ್ಲ | kasa biddilla (colloquial for placenta — validate) | UNSOURCED-linguistic"
    codemix:
      - "placenta nahi nikla | UNSOURCED-linguistic"
      - "placenta bandilla | UNSOURCED-linguistic"
    negations:   # ⚠ danger phrase contains negator
      - "आँवल निकल गई | aanval nikal gayi"
      - "ಮಾಸು ಬಿತ್ತು | maasu bittu"

  # ───────── POSTNATAL MOTHER ─────────
  pnc_heavy_bleeding:
    hi:
      - "बहुत ज्यादा खून का बहना | bahut zyaada khoon ka behna | OFFICIAL-M6HI p.39"
      - "एक दिन में पाँच से अधिक पैड बदलती है | ek din mein paanch se adhik pad badalti hai | OFFICIAL-M6HI p.39"
      - "खून के थक्के आ रहे | khoon ke thakke aa rahe | UNSOURCED-linguistic"
      - "कपड़ा भीग जाता है | kapda bheeg jaata hai | UNSOURCED-linguistic"
    kn:
      - "ತುಂಬಾ ರಕ್ತ ಹೋಗ್ತಿದೆ | tumba rakta hogtide | UNSOURCED-linguistic"
      - "ಗಡ್ಡೆ ಗಡ್ಡೆ ರಕ್ತ ಬರ್ತಿದೆ | gadde gadde rakta bartide | UNSOURCED-linguistic"
      - "ದಿನಕ್ಕೆ ಆರು ಪ್ಯಾಡ್ ಬದಲಾಯಿಸಿದ್ಲು | dinakke aaru pad badalaayisidlu | UNSOURCED-linguistic"
    codemix:
      - "pad 6 change kiye aaj | UNSOURCED-linguistic"
      - "bleeding jaasti ide, clots bartide | UNSOURCED-linguistic"
    negations:
      - "खून कम हो गया, नॉर्मल है | khoon kam ho gaya, normal hai"
      - "ರಕ್ತ ಕಡಿಮೆ ಆಗಿದೆ | rakta kadime aagide"
      - "NOTE: 'kam ho gaya' = reducing (normal lochia pattern) but 'phir se zyaada' / 'matte jaasti' = return of heavy bleeding = DANGER (INT26 p.11)"

  pnc_foul_lochia:
    hi:
      - "स्राव बदबूदार है | sraav badboodaar hai | OFFICIAL-M6HI p.39"
      - "बदबूदार स्राव के साथ ज्वर, ठंड लगना, पेट में दर्द | badboodaar sraav ke saath jvar, thand lagna, pet mein dard | OFFICIAL-M6HI p.39"
    kn:
      - "ಕೆಳಗಿಂದ ಕೆಟ್ಟ ವಾಸನೆ ಬರ್ತಿದೆ | kelaginda ketta vaasane bartide | UNSOURCED-linguistic"
    codemix:
      - "discharge mein smell | UNSOURCED-linguistic"
      - "smell bartide | UNSOURCED-linguistic"
    negations:
      - "बदबू नहीं | badboo nahi"
      - "ವಾಸನೆ ಇಲ್ಲ | vaasane illa"

  pnc_fever:
    hi:
      - "ज्वर / बुखार | jvar / bukhaar | OFFICIAL-M6HI p.39 (ज्वर)"
      - "ठंड लग के बुखार | thand lag ke bukhaar | UNSOURCED-linguistic"
    kn:
      - "ಜ್ವರ ಬಂದಿದೆ | jvara bandide | UNSOURCED-linguistic"
      - "ಮೈ ಬಿಸಿ ಇದೆ | mai bisi ide | UNSOURCED-linguistic"
    codemix:
      - "fever 102 hai | UNSOURCED-linguistic"
      - "fever ide | UNSOURCED-linguistic"
    negations:
      - "बुखार नहीं | bukhaar nahi"
      - "ಜ್ವರ ಇಲ್ಲ | jvara illa"

  pnc_convulsions_unconscious:
    hi:
      - "ऐंठन होना | ainthan hona | OFFICIAL-M6HI p.39"
      - "दौरा पड़ा, बेहोश हो गई | daura pada, behosh ho gayi | UNSOURCED-linguistic"
      - "झटके | jhatke | UNSOURCED-linguistic"
    kn:
      - "ಫಿಟ್ಸ್ ಬಂತು | fits bantu | UNSOURCED-linguistic"
      - "ಪ್ರಜ್ಞೆ ತಪ್ಪಿದಳು | prajne tappidalu | UNSOURCED-linguistic"
    codemix:
      - "fits aaye, unconscious ho gayi | UNSOURCED-linguistic"
      - "fits bantu, conscious illa | UNSOURCED-linguistic"
    negations:
      - "कोई दौरा नहीं | koi daura nahi"
      - "fits illa"

  pnc_headache_blurred_vision:
    hi:
      - "गंभीर सिरदर्द होना और धुंधला दिखाई देना | gambhir sirdard hona aur dhundhla dikhai dena | OFFICIAL-M6HI p.39"
    kn:
      - "ತಲೆ ನೋವು ಜಾಸ್ತಿ, ಕಣ್ಣು ಮಂಜು | tale novu jaasti, kannu manju | UNSOURCED-linguistic"
    codemix:
      - "headache + blurry vision | UNSOURCED-linguistic"
    negations:
      - "sir dard nahi / tale novu illa"

  pnc_swelling_face_hands:
    hi:
      - "चेहरे और हाथों पर सूजन | chehre aur haathon par soojan | OFFICIAL-M6HI p.39"
    kn:
      - "ಮುಖ ಕೈ ಕಾಲು ಊದಿಕೊಂಡಿದೆ | mukha kai kaalu oodikondide | UNSOURCED-linguistic"
    codemix:
      - "face swelling hai / swelling ide | UNSOURCED-linguistic"
    negations:
      - "सूजन नहीं / ಬಾವು ಇಲ್ಲ"

  pnc_breathing_difficulty:
    hi:
      - "साँस फूल रही | saans phool rahi | UNSOURCED-linguistic"
    kn:
      - "ಉಸಿರು ಕಟ್ಟುತ್ತಿದೆ | usiru kattuttide | UNSOURCED-linguistic"
    codemix:
      - "breathing problem | UNSOURCED-linguistic"
    negations:
      - "saans theek hai / usiru sari ide"

  pnc_severe_abdominal_pain:
    hi:
      - "पेट में तेज़ दर्द, बढ़ता जा रहा | pet mein tez dard, badhta ja raha | UNSOURCED-linguistic"
    kn:
      - "ಹೊಟ್ಟೆ ನೋವು ಜಾಸ್ತಿ ಆಗ್ತಿದೆ | hotte novu jaasti aagtide | UNSOURCED-linguistic"
    codemix:
      - "stomach pain badh raha / jaasti aagtide | UNSOURCED-linguistic"
    negations:
      - "pet dard nahi / hotte novu illa"
      - "NOTE: mild after-pains while breastfeeding are normal (INT26 p.12)"

  pnc_no_urine:   # ⚠ danger phrase contains negator
    hi:
      - "डिलीवरी के बाद पेशाब नहीं हुआ | delivery ke baad peshaab nahi hua | UNSOURCED-linguistic"
      - "पेशाब रुक गया | peshaab ruk gaya | UNSOURCED-linguistic"
    kn:
      - "ಹೆರಿಗೆ ಆದ್ಮೇಲೆ ಉಚ್ಚೆ ಹೋಗಿಲ್ಲ | herige aadmele uchche hogilla | UNSOURCED-linguistic"
      - "ಮೂತ್ರ ಆಗಿಲ್ಲ | mootra aagilla | UNSOURCED-linguistic"
    codemix:
      - "urine pass nahi hua | UNSOURCED-linguistic"
      - "urine aagilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "पेशाब हो गया | peshaab ho gaya"
      - "ಉಚ್ಚೆ ಹೋಯ್ತು | uchche hoytu"

  pnc_urinary_burning_leg_swelling:
    hi:
      - "पेशाब में जलन और पैर में सूजन-दर्द | peshaab mein jalan aur pair mein soojan-dard | UNSOURCED-linguistic"
    kn:
      - "ಉರಿ ಮೂತ್ರ, ಕಾಲು ಬಾವು ನೋವು | uri mootra, kaalu baavu novu | UNSOURCED-linguistic"
    codemix:
      - "urine burning + leg swelling | UNSOURCED-linguistic"
    negations:
      - "jalan nahi / uri illa"

  pnc_pallor_weakness:
    hi:
      - "माता का रंग पीला पड़ गया (= pale) | maata ka rang peela pad gaya | OFFICIAL-M6HI p.39"
      - "बहुत कमजोरी, चक्कर | bahut kamzori, chakkar | UNSOURCED-linguistic"
    kn:
      - "ತುಂಬಾ ಸುಸ್ತು, ತಲೆ ಸುತ್ತು | tumba sustu, tale suttu | UNSOURCED-linguistic"
      - "ಬಿಳಿಚಿಕೊಂಡಿದ್ದಾಳೆ | bilichikondiddaale | UNSOURCED-linguistic"
    codemix:
      - "weakness bahut hai | UNSOURCED-linguistic"
      - "tumba weak aagidaale | UNSOURCED-linguistic"
    negations:
      - "kamzori nahi / sustu illa"
      - "NOTE: Hindi 'peela padna' = pallor (anaemia) here, but 'peeliya' = jaundice; do not conflate"

  pnc_jaundice:
    hi:
      - "आँखें पीली, पेशाब पीला | aankhen peeli, peshaab peela | UNSOURCED-linguistic"
      - "पीलिया | peeliya | UNSOURCED-linguistic"
    kn:
      - "ಕಾಮಾಲೆ | kaamaale | UNSOURCED-linguistic"
      - "ಕಣ್ಣು ಹಳದಿ ಆಗಿದೆ | kannu haladi aagide | UNSOURCED-linguistic"
    codemix:
      - "jaundice hai / jaundice ide | UNSOURCED-linguistic"
    negations:
      - "peeliya nahi / kaamaale illa"

  pnc_abnormal_behaviour_harm_thoughts:
    hi:
      - "उल्टा-सीधा बोल रही है | ulta-seedha bol rahi hai | UNSOURCED-linguistic"
      - "बच्चे को कुछ कर दूँगी बोलती है | bachche ko kuch kar doongi bolti hai | UNSOURCED-linguistic"
      - "गुमसुम रहती है, खाना-सोना नहीं | gumsum rehti hai, khaana-sona nahi | UNSOURCED-linguistic"
    kn:
      - "ಹುಚ್ಚು ಹುಚ್ಚಾಗಿ ಮಾತಾಡ್ತಾಳೆ | huchchu huchchaagi maataadtaale | UNSOURCED-linguistic"
      - "ಮಂಕಾಗಿದ್ದಾಳೆ, ಊಟ ನಿದ್ದೆ ಇಲ್ಲ | mankaagiddaale, oota nidde illa | UNSOURCED-linguistic"
      - "ಸಾಯ್ತೀನಿ ಅಂತಾಳೆ | saayteeni antaale | UNSOURCED-linguistic"
    codemix:
      - "depression jaisa lag raha | UNSOURCED-linguistic"
      - "tumba upset aagidaale, baby ge harm maadtini antaale | UNSOURCED-linguistic"
    negations:
      - "khush hai, theek se baat kar rahi"
      - "chennaagi maataadtaale"

  pnc_breast_problem_fever:
    hi:
      - "स्तन में गाँठ और संक्रमण | stan mein gaanth aur sankraman | OFFICIAL-M6HI p.39 (heading)"
      - "छाती में गाँठ, दर्द, बुखार | chhaati mein gaanth, dard, bukhaar | UNSOURCED-linguistic"
      - "निप्पल फट गए | nipple phat gaye | UNSOURCED-linguistic"
    kn:
      - "ಮೊಲೆ ಗಟ್ಟಿ ಆಗಿದೆ, ನೋವು, ಜ್ವರ | mole gatti aagide, novu, jvara | UNSOURCED-linguistic"
      - "ಮೊಲೆತೊಟ್ಟು ಒಡೆದಿದೆ | moletottu odedide | UNSOURCED-linguistic"
    codemix:
      - "breast pain + fever | UNSOURCED-linguistic"
    negations:
      - "dard nahi / novu illa"

  pnc_perineal_infection:
    hi:
      - "टाँकों में सूजन, मवाद | taankon mein soojan, mavaad | UNSOURCED-linguistic"
    kn:
      - "ಹೊಲಿಗೆ ಹತ್ರ ಬಾವು, ಕೀವು | holige hatra baavu, keevu | UNSOURCED-linguistic"
    codemix:
      - "stitches mein pus | UNSOURCED-linguistic"
      - "stitch alli pus | UNSOURCED-linguistic"
    negations:
      - "taanke theek hain / holige sari ide"

  pnc_not_eating_vomiting:
    hi:
      - "कल से कुछ नहीं खाया | kal se kuch nahi khaaya | UNSOURCED-linguistic"
      - "बार-बार उल्टी | baar-baar ulti | UNSOURCED-linguistic"
    kn:
      - "ನಿನ್ನೆಯಿಂದ ಏನೂ ತಿಂದಿಲ್ಲ | ninneyinda enu tindilla | UNSOURCED-linguistic"
      - "ಪದೇ ಪದೇ ವಾಂತಿ | pade pade vaanti | UNSOURCED-linguistic"
    codemix:
      - "food nahi le rahi | UNSOURCED-linguistic"
      - "oota maadtilla, vomiting | UNSOURCED-linguistic"
    negations:   # ⚠ partially
      - "theek se kha rahi hai"
      - "chennaagi oota maadtaale"

  pnc_stool_incontinence:
    hi:
      - "टट्टी अपने आप निकल जाती | tatti apne aap nikal jaati | UNSOURCED-linguistic"
    kn:
      - "ಮಲ ತಡೆಯೋಕೆ ಆಗ್ತಿಲ್ಲ | mala tadeyoke aagtilla | UNSOURCED-linguistic"
    codemix:
      - "motion control nahi | UNSOURCED-linguistic"
    negations:
      - "control hai / control ide"

  # ───────── NEWBORN ─────────
  nb_fast_breathing:
    hi:
      - "बच्चा तेज़-तेज़ साँस ले रहा | bachcha tez-tez saans le raha | UNSOURCED-linguistic"
      - "साँस जल्दी-जल्दी चल रही | saans jaldi-jaldi chal rahi | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ಬೇಗ ಬೇಗ ಉಸಿರಾಡ್ತಿದೆ | magu bega bega usiraadtide | UNSOURCED-linguistic"
      - "ಏದುಸಿರು ಬಿಡ್ತಿದೆ | edusiru bidtide | UNSOURCED-linguistic"
    codemix:
      - "breathing fast hai, 64 count kiya | UNSOURCED-linguistic"
      - "breathing fast ide, 65 ide | UNSOURCED-linguistic"
    negations:
      - "साँस नॉर्मल है | saans normal hai"
      - "ಉಸಿರಾಟ ಸರಿ ಇದೆ | usiraata sari ide"
      - "NOTE: a spoken count (e.g. 'saath se upar', 'aravattu') must be parsed: see 02-vocab-numbers.md"

  nb_chest_indrawing:
    hi:
      - "छाती में धंसाव | chhaati mein dhansaav | OFFICIAL-M7HI p.55"
      - "पसली चल रही है | pasli chal rahi hai | UNSOURCED-linguistic (widely used folk term; could not verify in a source)"
      - "साँस लेते समय छाती अंदर जाती है | saans lete samay chhaati andar jaati hai | UNSOURCED-linguistic"
    kn:
      - "ಉಸಿರಾಡುವಾಗ ಎದೆ ಒಳಗೆ ಹೋಗ್ತಿದೆ | usiraaduvaaga ede olage hogtide | UNSOURCED-linguistic"
      - "ಪಕ್ಕೆಲುಬು ಒಳಗೆ ಎಳೀತಿದೆ | pakkelubu olage eleetide | UNSOURCED-linguistic"
    codemix:
      - "chest andar ja raha | UNSOURCED-linguistic"
      - "chest indrawing ide | UNSOURCED-linguistic"
    negations:
      - "छाती में धंसाव नहीं | chhaati mein dhansaav nahi"
      - "ಎದೆ ಒಳಗೆ ಹೋಗ್ತಿಲ್ಲ | ede olage hogtilla"

  nb_grunting_nasal_flaring:
    hi:
      - "साँस में कराहने/घुरघुर की आवाज़ | saans mein karaahne / ghurghur ki aawaaz | UNSOURCED-linguistic"
      - "नाक फूल रही | naak phool rahi | UNSOURCED-linguistic"
    kn:
      - "ಉಸಿರಾಡುವಾಗ ಕುಂಯ್ ಕುಂಯ್ ಶಬ್ದ | usiraaduvaaga kuny kuny shabda | UNSOURCED-linguistic"
      - "ಮೂಗು ಅರಳ್ತಿದೆ | moogu araltide | UNSOURCED-linguistic"
    codemix:
      - "grunting sound aa raha / grunting ide | UNSOURCED-linguistic"
    negations:
      - "koi aawaaz nahi / shabda illa"

  nb_cyanosis:
    hi:
      - "होंठ नीले पड़ गए | honth neele pad gaye | UNSOURCED-linguistic"
    kn:
      - "ತುಟಿ ನೀಲಿ ಆಗಿದೆ | tuti neeli aagide | UNSOURCED-linguistic"
    codemix:
      - "lips blue ho gaye / lips blue aagide | UNSOURCED-linguistic"
    negations:
      - "rang theek hai, gulaabi hai / banna sari ide"

  nb_apnoea_slow_breathing:
    hi:
      - "साँस रुक-रुक के ले रहा | saans ruk-ruk ke le raha | UNSOURCED-linguistic"
    kn:
      - "ಉಸಿರು ನಿಂತು ನಿಂತು ಬರ್ತಿದೆ | usiru nintu nintu bartide | UNSOURCED-linguistic"
    codemix:
      - "breathing stop ho jaati hai beech mein | UNSOURCED-linguistic"
    negations:
      - "saans theek chal rahi / usiru sari ide"

  nb_fever:
    hi:
      - "उसे बुखार हो | use bukhaar ho | OFFICIAL-M7HI p.55"
      - "बच्चा तप रहा है | bachcha tap raha hai | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ಮೈ ಬಿಸಿ ಇದೆ | magu mai bisi ide | UNSOURCED-linguistic"
      - "ಮಗುಗೆ ಜ್ವರ | maguge jvara | UNSOURCED-linguistic"
    codemix:
      - "baby ko fever hai / baby ge fever | UNSOURCED-linguistic"
    negations:
      - "बुखार नहीं | bukhaar nahi"
      - "ಜ್ವರ ಇಲ್ಲ | jvara illa"

  nb_hypothermia:
    hi:
      - "छूने से ठंडा महसूस होता हो | chhoone se thanda mehsoos hota ho | OFFICIAL-M7HI p.55"
      - "हाथ-पैर ठंडे पड़ गए | haath-pair thande pad gaye | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ತಣ್ಣಗಿದೆ | magu tannagide | UNSOURCED-linguistic"
      - "ಕೈಕಾಲು ತಣ್ಣಗಾಗಿದೆ | kaikaalu tannagaagide | UNSOURCED-linguistic"
    codemix:
      - "baby cold hai / baby cold aagide | UNSOURCED-linguistic"
    negations:
      - "garam hai, theek hai / bechchagide"

  nb_poor_feeding:   # ⚠ danger phrase contains negator
    hi:
      - "दूध पीना बंद कर दिया | doodh peena band kar diya | OFFICIAL-M7HI p.55"
      - "बच्चा दूध नहीं खींच रहा | bachcha doodh nahi kheench raha | UNSOURCED-linguistic"
      - "स्तन नहीं पकड़ रहा | stan nahi pakad raha | UNSOURCED-linguistic"
      - "चूसने में कमज़ोर | choosne mein kamzor | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ಹಾಲು ಕುಡೀತಿಲ್ಲ | magu haalu kudeetilla | UNSOURCED-linguistic"
      - "ಮೊಲೆ ಚೀಪ್ತಿಲ್ಲ | mole cheeptilla | UNSOURCED-linguistic"
      - "ಹಾಲು ಎಳೀತಿಲ್ಲ | haalu eleetilla | UNSOURCED-linguistic"
    codemix:
      - "feed nahi le raha / feeding kam | UNSOURCED-linguistic"
      - "feed maadtilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "अच्छे से दूध पी रहा है | achchhe se doodh pee raha hai"
      - "ಚೆನ್ನಾಗಿ ಹಾಲು ಕುಡೀತಿದೆ | chennaagi haalu kudeetide"

  nb_lethargy_limp:
    hi:
      - "शिशु के हाथ-पैर शिथिल हो गए | shishu ke haath-pair shithil ho gaye | OFFICIAL-M7HI p.55"
      - "सुस्त या बेहोश | sust ya behosh | OFFICIAL-M7HI p.20"
      - "बच्चा ढीला पड़ गया, जगाने पर भी नहीं उठता | bachcha dheela pad gaya, jagaane par bhi nahi uthta | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ಜೋತು ಬಿದ್ದಿದೆ | magu jotu biddide | UNSOURCED-linguistic"
      - "ಎಬ್ಬಿಸಿದರೂ ಏಳ್ತಿಲ್ಲ | ebbisidaroo eltilla | UNSOURCED-linguistic"
      - "ಮಗು ಚುರುಕಾಗಿಲ್ಲ | magu churukaagilla | UNSOURCED-linguistic"
    codemix:
      - "baby active nahi hai | UNSOURCED-linguistic"
      - "baby dull aagide | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "बच्चा चुस्त है, हाथ-पैर चला रहा | bachcha chust hai, haath-pair chala raha"
      - "ಮಗು ಚುರುಕಾಗಿದೆ | magu churukaagide"

  nb_weak_cry:
    hi:
      - "रोना कमज़ोर / रोना बंद | rona kamzor / rona band | UNSOURCED-linguistic (HBNC Hindi form wording not checked)"
    kn:
      - "ಅಳು ಸಣ್ಣದಾಗಿದೆ | alu sannadaagide | UNSOURCED-linguistic"
      - "ಮಗು ಅಳ್ತಾನೇ ಇಲ್ಲ | magu altaane illa | UNSOURCED-linguistic"
    codemix:
      - "cry weak hai / cry weak ide | UNSOURCED-linguistic"
    negations:   # ⚠
      - "ज़ोर से रोता है | zor se rota hai"
      - "ಜೋರಾಗಿ ಅಳ್ತದೆ | joraagi altade"

  nb_convulsions:
    hi:
      - "शरीर में ऐंठन (कन्वल्शन) | shareer mein ainthan (convulsion) | OFFICIAL-M7HI p.20"
      - "बच्चे को झटके आ रहे | bachche ko jhatke aa rahe | UNSOURCED-linguistic"
      - "आँखें ऊपर चढ़ गईं | aankhen upar chadh gayi | UNSOURCED-linguistic"
    kn:
      - "ಮಗುಗೆ ಫಿಟ್ಸ್ ಬಂತು | maguge fits bantu | UNSOURCED-linguistic"
      - "ಕಣ್ಣು ಮೇಲೆ ಮಾಡ್ತಿತ್ತು, ಕೈಕಾಲು ಅದುರ್ತಿತ್ತು | kannu mele maadtittu, kaikaalu adurtittu | UNSOURCED-linguistic"
    codemix:
      - "baby ko fits / baby ge fits | UNSOURCED-linguistic"
    negations:
      - "jhatke nahi / fits illa"

  nb_jaundice_severe:
    hi:
      - "हथेली और तलवे पीले | hatheli aur talve peele | UNSOURCED-linguistic (MCP Hindi wording not checked)"
      - "बच्चा पीला पड़ गया, पीलिया | bachcha peela pad gaya, peeliya | UNSOURCED-linguistic"
    kn:
      - "ಅಂಗೈ ಅಂಗಾಲು ಹಳದಿ | angai angaalu haladi | UNSOURCED-linguistic"
      - "ಮಗುಗೆ ಕಾಮಾಲೆ | maguge kaamaale | UNSOURCED-linguistic"
      - "ಮಗು ಹಳದಿ ಆಗಿದೆ | magu haladi aagide | UNSOURCED-linguistic"
    codemix:
      - "baby ko jaundice, palms yellow | UNSOURCED-linguistic"
      - "jaundice ide, kaalu yellow | UNSOURCED-linguistic"
    negations:
      - "पीलापन नहीं | peelapan nahi"
      - "ಹಳದಿ ಇಲ್ಲ | haladi illa"
      - "NOTE: Hindi 'peela pad gaya' for a newborn usually = jaundice; for a mother usually = pallor. Disambiguate by group."

  nb_blood_in_stool:
    hi:
      - "टट्टी में खून | tatti mein khoon | UNSOURCED-linguistic"
    kn:
      - "ಕಕ್ಕದಲ್ಲಿ ರಕ್ತ | kakkadalli rakta | UNSOURCED-linguistic"
    codemix:
      - "potty mein blood / motion alli blood | UNSOURCED-linguistic"
    negations:
      - "khoon nahi / rakta illa"

  nb_bleeding_any_site:
    hi:
      - "नाक/मुँह से खून | naak/munh se khoon | UNSOURCED-linguistic"
      - "नाल से खून | naal se khoon | UNSOURCED-linguistic"
    kn:
      - "ಮೂಗು ಬಾಯಿಂದ ರಕ್ತ | moogu baayinda rakta | UNSOURCED-linguistic"
      - "ಹೊಕ್ಕುಳ ಬಳ್ಳಿಯಿಂದ ರಕ್ತ | hokkula balliyinda rakta | UNSOURCED-linguistic"
    codemix:
      - "cord se bleeding / cord bleeding | UNSOURCED-linguistic"
    negations:
      - "khoon nahi / rakta illa"

  nb_umbilical_infection:
    hi:
      - "नाभि लाल है, मवाद आ रहा | naabhi laal hai, mavaad aa raha | UNSOURCED-linguistic"
      - "नाल पक गई | naal pak gayi | UNSOURCED-linguistic"
    kn:
      - "ಹೊಕ್ಕುಳ ಕೆಂಪಾಗಿದೆ, ಕೀವು | hokkula kempaagide, keevu | UNSOURCED-linguistic"
    codemix:
      - "cord mein pus / cord alli pus | UNSOURCED-linguistic"
    negations:
      - "naabhi sookhi aur saaf / hokkula onagide"

  nb_skin_pustules:
    hi:
      - "शरीर पर बहुत सी फुंसियाँ, बड़ा फोड़ा | shareer par bahut si phunsiyaan, bada phoda | UNSOURCED-linguistic"
    kn:
      - "ಮೈ ಮೇಲೆ ಕೀವು ಗುಳ್ಳೆ, ದೊಡ್ಡ ಕುರು | mai mele keevu gulle, dodda kuru | UNSOURCED-linguistic"
    codemix:
      - "pus wale daane / pus gulle | UNSOURCED-linguistic"
    negations:
      - "koi phunsi nahi / gulle illa"

  nb_no_urine_stool:   # ⚠ danger phrase contains negator
    hi:
      - "पेशाब-टट्टी नहीं हुई | peshaab-tatti nahi hui | UNSOURCED-linguistic"
    kn:
      - "ಉಚ್ಚೆ ಕಕ್ಕ ಮಾಡಿಲ್ಲ | uchche kakka maadilla | UNSOURCED-linguistic"
    codemix:
      - "urine pass nahi kiya / urine motion aagilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "peshaab theek kar raha"
      - "uchche maadtide"

  nb_abdominal_distension_vomiting:
    hi:
      - "पेट फूल गया, बार-बार उल्टी | pet phool gaya, baar-baar ulti | UNSOURCED-linguistic"
    kn:
      - "ಹೊಟ್ಟೆ ಉಬ್ಬಿದೆ, ಪದೇ ಪದೇ ವಾಂತಿ | hotte ubbide, pade pade vaanti | UNSOURCED-linguistic"
    codemix:
      - "stomach bloated, vomiting | UNSOURCED-linguistic"
    negations:
      - "pet naram hai / hotte sari ide"
      - "NOTE: small spit-ups after feeds are normal"

  nb_diarrhoea:
    hi:
      - "पतले दस्त | patle dast | UNSOURCED-linguistic"
    kn:
      - "ಭೇದಿ ಆಗ್ತಿದೆ, ನೀರು ನೀರಾಗಿ ಕಕ್ಕ | bhedi aagtide, neeru neeraagi kakka | UNSOURCED-linguistic"
    codemix:
      - "loose motion | UNSOURCED-linguistic"
    negations:
      - "dast nahi / bhedi illa"
      - "NOTE: breastfed newborns pass frequent soft stools normally"

  nb_eye_discharge:
    hi:
      - "आँख में कीचड़/मवाद, सूजन | aankh mein keechad/mavaad, soojan | UNSOURCED-linguistic"
    kn:
      - "ಕಣ್ಣಲ್ಲಿ ಪಿಸುರು/ಕೀವು, ಕೆಂಪು | kannalli pisuru/keevu, kempu | UNSOURCED-linguistic"
    codemix:
      - "eye se pus / eye red ide | UNSOURCED-linguistic"
    negations:
      - "aankh saaf hai / kannu sari ide"

  nb_very_low_birth_weight:
    hi:
      - "बच्चा बहुत कम वज़न का | bachcha bahut kam vazan ka | UNSOURCED-linguistic"
    kn:
      - "ಮಗು ತೂಕ ತುಂಬಾ ಕಡಿಮೆ | magu tooka tumba kadime | UNSOURCED-linguistic"
    codemix:
      - "weight 1.6 kg / 1600 gram | UNSOURCED-linguistic (numeric parse)"
    negations:
      - "weight theek hai, 3 kilo / tooka sari ide"

  nb_tetanus_stiffness:
    hi:
      - "मुँह नहीं खोल रहा, शरीर अकड़ गया | munh nahi khol raha, shareer akad gaya | UNSOURCED-linguistic"
    kn:
      - "ಬಾಯಿ ತೆಗೀತಿಲ್ಲ, ಮೈ ಗಟ್ಟಿ ಆಗಿದೆ | baayi tegeetilla, mai gatti aagide | UNSOURCED-linguistic"
    codemix:
      - "body stiff, mouth open nahi / body stiff aagide | UNSOURCED-linguistic"
    negations:
      - "body naram hai / mai sadila (CAUTION: 'sadila' = limp, could itself be a danger sign)"

  nb_bulging_fontanelle:
    hi:
      - "तालू उभरा हुआ | taaloo ubhra hua | UNSOURCED-linguistic"
    kn:
      - "ನೆತ್ತಿ ಉಬ್ಬಿದೆ | netti ubbide | UNSOURCED-linguistic"
    codemix:
      - "head pe soft spot phoola / soft spot ubbide | UNSOURCED-linguistic"
    negations:
      - "taaloo theek / netti sari ide"

  nb_birth_asphyxia:   # ⚠
    hi:
      - "पैदा होते ही रोया नहीं, साँस नहीं | paida hote hi roya nahi, saans nahi | UNSOURCED-linguistic"
    kn:
      - "ಹುಟ್ಟಿದ ತಕ್ಷಣ ಅಳಲಿಲ್ಲ, ಉಸಿರಾಡಲಿಲ್ಲ | huttida takshana alalilla, usiraadalilla | UNSOURCED-linguistic"
    codemix:
      - "birth pe cry nahi kiya / cry maadlilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "turant roya / takshana attu"

  # ───────── CHILD 2–59 MONTHS ─────────
  ch_unable_to_drink:   # ⚠
    hi:
      - "कुछ भी पीने या स्तनपान करने में असमर्थ | kuch bhi peene ya stanpaan karne mein asamarth | OFFICIAL-M7HI p.20"
      - "कुछ भी नहीं पी रहा | kuch bhi nahi pee raha | UNSOURCED-linguistic"
    kn:
      - "ಏನೂ ಕುಡೀತಿಲ್ಲ, ಹಾಲೂ ಕುಡೀತಿಲ್ಲ | enu kudeetilla, haaloo kudeetilla | UNSOURCED-linguistic"
    codemix:
      - "kuch drink nahi kar raha / drink maadtilla | UNSOURCED-linguistic"
    negations:   # NORMAL phrasing
      - "पानी-दूध पी रहा है | paani-doodh pee raha hai"
      - "ಕುಡೀತಿದೆ | kudeetide"

  ch_vomits_everything:
    hi:
      - "जो भी पीने को दिया जाय वह उल्टी कर देता है | jo bhi peene ko diya jaay vah ulti kar deta hai | OFFICIAL-M7HI p.20"
      - "सब उल्टी कर देता है | sab ulti kar deta hai | UNSOURCED-linguistic"
    kn:
      - "ಕುಡಿದಿದ್ದೆಲ್ಲಾ ವಾಂತಿ ಮಾಡ್ತಿದೆ | kudididdellaa vaanti maadtide | UNSOURCED-linguistic"
    codemix:
      - "jo bhi do vomit / yen kottru vomit | UNSOURCED-linguistic"
    negations:
      - "ulti nahi / vaanti illa"
      - "NOTE: 'ek do baar ulti' (vomits sometimes) is NOT this sign"

  ch_convulsions:
    hi:
      - "शरीर में ऐंठन (कन्वल्शन) | shareer mein ainthan (convulsion) | OFFICIAL-M7HI p.20"
      - "झटके / मिर्गी जैसा | jhatke / mirgi jaisa | UNSOURCED-linguistic"
    kn:
      - "ಫಿಟ್ಸ್ ಬಂತು / ಸೆಳವು | fits bantu / selavu | UNSOURCED-linguistic"
    codemix:
      - "fits aaye / fits bantu | UNSOURCED-linguistic"
    negations:
      - "jhatke nahi / fits illa"

  ch_lethargic_unconscious:
    hi:
      - "सुस्त या बेहोश | sust ya behosh | OFFICIAL-M7HI p.20"
    kn:
      - "ಮಂಕಾಗಿ ಮಲಗಿದೆ, ಪ್ರಜ್ಞೆ ಇಲ್ಲ | mankaagi malagide, prajne illa | UNSOURCED-linguistic"
    codemix:
      - "baby unconscious hai / response illa | UNSOURCED-linguistic"
    negations:   # ⚠ 'prajne illa' is DANGER
      - "खेल रहा है, चुस्त है | khel raha hai, chust hai"
      - "ಆಟ ಆಡ್ತಿದೆ | aata aadtide"

  ch_chest_indrawing:
    hi:
      - "पसली चल रही / छाती अंदर धंस रही | pasli chal rahi / chhaati andar dhans rahi | UNSOURCED-linguistic"
    kn:
      - "ಎದೆ ಒಳಗೆ ಹೋಗ್ತಿದೆ | ede olage hogtide | UNSOURCED-linguistic"
    codemix:
      - "chest indrawing hai / ide | UNSOURCED-linguistic"
    negations:
      - "chhaati nahi dhans rahi / ede olage hogtilla"

  ch_fast_breathing:
    hi:
      - "तेज़ साँस / साँस फूलना | tez saans / saans phoolna | UNSOURCED-linguistic"
      - "निमोनिया (lay umbrella term) | nimoniya | SECONDARY: PLOS ONE 2015 (UP/Bihar) reports 'pneumonia' itself is the common lay term"
    kn:
      - "ಬೇಗ ಬೇಗ ಉಸಿರು | bega bega usiru | UNSOURCED-linguistic"
      - "ನ್ಯುಮೋನಿಯಾ | nyumoniya | UNSOURCED-linguistic"
    codemix:
      - "breathing fast, 52 count / breathing fast ide | UNSOURCED-linguistic"
    negations:
      - "saans normal / usiraata sari"

  ch_fever_persistent:
    hi:
      - "तीन दिन से रोज़ बुखार | teen din se roz bukhaar | UNSOURCED-linguistic"
      - "हफ़्ते भर से बुखार नहीं उतर रहा | hafte bhar se bukhaar nahi utar raha | UNSOURCED-linguistic"
    kn:
      - "ಮೂರು ದಿನದಿಂದ ಜ್ವರ ಬಿಟ್ಟಿಲ್ಲ | mooru dinadinda jvara bittilla | UNSOURCED-linguistic"
    codemix:
      - "fever 3 din se / fever 3 days inda | UNSOURCED-linguistic"
    negations:
      - "बुखार उतर गया | bukhaar utar gaya"
      - "ಜ್ವರ ಬಿಟ್ಟಿದೆ | jvara bittide"
      - "NOTE: 'bukhaar nahi utar raha' / 'jvara bittilla' contain negators but mean fever PERSISTS = danger"

  ch_stiff_neck:
    hi:
      - "गर्दन अकड़ गई, मुड़ नहीं रही | gardan akad gayi, mud nahi rahi | UNSOURCED-linguistic"
    kn:
      - "ಕುತ್ತಿಗೆ ಬಿಗಿದಿದೆ, ತಿರುಗಿಸೋಕೆ ಆಗಲ್ಲ | kuttige bigidide, tirugisoke aagalla | UNSOURCED-linguistic"
    codemix:
      - "neck stiff hai / neck stiff ide | UNSOURCED-linguistic"
    negations:
      - "gardan theek ghoom rahi / kuttige sari tirugatte"

  ch_severe_dehydration:
    hi:
      - "आँखें धँस गईं, बहुत सुस्त, पानी नहीं पी पा रहा | aankhen dhans gayi, bahut sust, paani nahi pee pa raha | UNSOURCED-linguistic"
      - "चमड़ी खींचने पर धीरे लौटती | chamdi kheenchne par dheere lautti | UNSOURCED-linguistic"
    kn:
      - "ಕಣ್ಣು ಗುಳಿ ಬಿದ್ದಿದೆ, ತುಂಬಾ ಸುಸ್ತು | kannu guli biddide, tumba sustu | UNSOURCED-linguistic"
    codemix:
      - "dehydration lag raha, eyes sunken / eyes sunken aagide | UNSOURCED-linguistic"
    negations:
      - "aankhen theek, paani pee raha / kannu sari ide"

  ch_persistent_diarrhoea:
    hi:
      - "दो हफ़्ते से दस्त | do hafte se dast | UNSOURCED-linguistic"
    kn:
      - "ಎರಡು ವಾರದಿಂದ ಭೇದಿ | eradu vaaradinda bhedi | UNSOURCED-linguistic"
    codemix:
      - "loose motion 14 din se / 2 weeks inda | UNSOURCED-linguistic"
    negations:
      - "dast band / bhedi nintide"

  ch_blood_in_stool:
    hi:
      - "दस्त में खून | dast mein khoon | UNSOURCED-linguistic"
      - "आँव-खून | aanv-khoon | UNSOURCED-linguistic"
    kn:
      - "ಭೇದಿಯಲ್ಲಿ ರಕ್ತ | bhediyalli rakta | UNSOURCED-linguistic"
    codemix:
      - "motion mein blood / motion alli blood | UNSOURCED-linguistic"
    negations:
      - "khoon nahi / rakta illa"

  ch_chronic_cough:
    hi:
      - "महीने भर से खाँसी | mahine bhar se khaansi | UNSOURCED-linguistic"
    kn:
      - "ಒಂದು ತಿಂಗಳಿಂದ ಕೆಮ್ಮು | ondu tingalinda kemmu | UNSOURCED-linguistic"
    codemix:
      - "cough 1 month se / cough 1 month inda | UNSOURCED-linguistic"
    negations:
      - "khaansi nahi / kemmu illa"

  ch_severe_acute_malnutrition:
    hi:
      - "दोनों पैरों में सूजन, बहुत दुबला | dono pairon mein soojan, bahut dubla | UNSOURCED-linguistic"
      - "लाल पट्टी में / कार्ड पर लाल | laal patti mein / card par laal | UNSOURCED-linguistic"
    kn:
      - "ಎರಡೂ ಕಾಲು ಬಾವು, ತುಂಬಾ ಸಣ್ಣಗಿದೆ | eradoo kaalu baavu, tumba sannagide | UNSOURCED-linguistic"
    codemix:
      - "MUAC red / red zone alli ide | UNSOURCED-linguistic"
    negations:
      - "green mein hai / green zone"

  ch_severe_pallor:
    hi:
      - "हथेली बिल्कुल सफेद | hatheli bilkul safed | UNSOURCED-linguistic"
    kn:
      - "ಅಂಗೈ ತುಂಬಾ ಬಿಳಿ | angai tumba bili | UNSOURCED-linguistic"
    codemix:
      - "palm white hai / palm bili ide | UNSOURCED-linguistic"
    negations:
      - "hatheli gulaabi / angai kempu"

  ch_aefi_serious:
    hi:
      - "टीके के बाद तेज़ बुखार/झटके/बहुत रोना | teeke ke baad tez bukhaar/jhatke/bahut rona | UNSOURCED-linguistic"
    kn:
      - "ಲಸಿಕೆ ಆದ್ಮೇಲೆ ಜೋರು ಜ್ವರ, ಫಿಟ್ಸ್, ನಿಲ್ಲದ ಅಳು | lasike aadmele joru jvara, fits, nillada alu | UNSOURCED-linguistic"
    codemix:
      - "injection ke baad fits / vaccine aadmele fits | UNSOURCED-linguistic"
    negations:
      - "teeke ke baad theek hai / lasike aadmele sari ide"
```

---

## Sources

Official Government of India sources, all downloaded and read:

1. **INT26**: *Integrated Training Module for ASHA 2026, Part B: Holding Hands Through Different Phases of Life.* MoHFW / NHSRC, 2026 (uploaded Oct 2026). https://www.nhsrcindia.org/sites/default/files/2026-10/Integrated%20ASHA%20Module%20Part%20B.pdf. Sections used: B.1.2 (p.6–10), B.1.3 (p.11–14), B.1.6 (p.27–29), B.1.10 "Danger signs in newborn and postnatal mother" (p.46–49), B.2.10 AEFI (p.98–102), B.2.14 Care of the Sick Child (p.123–127), B.4.2–4.3 ANC/High-risk (p.171–184). Parts A and C are at the same path but were not reviewed in depth.
2. **M6**: *ASHA Module 6: Skills that Save Lives* (English). MoHFW/NRHM, published by NHSRC; year not printed on the pages read (UNVERIFIED; commonly dated 2011). https://www.nhsrcindia.org/sites/default/files/2021-05/Skills%20that%20Save%20Lives%20ASHA%20Module%206%20English.pdf. The PDF is scanned and was read as page images: Part B §4 (p.30–33), §6 (p.38–40), Part C §2–3 (p.44–47), §5–6 (p.59–60). An official mirror at hbnc-hbyc.mohfw.gov.in/assets/document/ASHA_Training_Module_6.pdf was unreachable (connection refused).
3. **M6HI**: *ASHA Module 6* (Hindi). NHSRC. https://www.nhsrcindia.org/sites/default/files/2021-05/Skills%20that%20Save%20Lives%20ASHA%20Module%206%20Hindi.pdf. Read p.30, 31, 38, 39.
4. **M7**: *ASHA Module 7: Skills that Save Lives* (English). MoHFW/NRHM, NHSRC; revised edition including amoxicillin for young-infant sepsis, year UNVERIFIED. https://nhsrcindia.org/sites/default/files/2021-06/Skills%20That%20Save%20Lives%20ASHA%20Module-7%20English.pdf. Pages used: p.20 (general danger signs), p.22 (fever), p.25 (diarrhoea), p.29 (ARI), p.37 (post-abortion), p.54–56 (newborn sepsis / when to refer).
5. **M7HI**: *ASHA Module 7* (Hindi). NHSRC. https://www.nhsrcindia.org/sites/default/files/2021-05/Skills%20That%20Save%20Lives%20ASHA%20Module%207%20Hindi.pdf. Read p.20 and 55. The text layer uses a legacy Kruti-Dev font, so it was read from page images.
6. **HBNCH**: *Handbook for ASHA Facilitator and ANM/MPW on Home Based Newborn Care and Home Based Care for Young Child* (English). MoHFW/NHSRC, uploaded Feb 2023 (print year UNVERIFIED). https://www.nhsrcindia.org/sites/default/files/2023-02/Handbook%20for%20ASHA%20Facilitators%20and%20MPWs%20on%20HBNC%20and%20HBYC-English.pdf. Used Annexure 1b–1c, the HBNC recording/home-visit form (p.18–23). A Hindi version was downloaded but is image-only and was not read.
7. **MCP**: *Mother and Child Protection Card* (English). MoHFW & MWCD; NHM-hosted PDF created 5 Feb 2018. https://nhm.gov.in/New_Updates_2018/NHM_Components/Immunization/Guildelines_for_immunization/MCP_Card_English_version.pdf. pdf p.4 (pregnancy danger signs), p.5 (PNC record), p.24–25 (growth chart / during illness), p.28 (newborn danger signs). The "Revised India MCP Card English (28-05-2018)" at hbnc-hbyc.mohfw.gov.in could not be reached, so it is UNVERIFIED whether its wording is identical.
8. **FIMNCI**: *Facility Based IMNCI (F-IMNCI) Chart Booklet.* MoHFW / WHO / UNICEF, n.d. (PDF created 2012). Accessed via a **SECONDARY host** mirror: https://medbox.org/index.php/dl/5e148832db60a2044c2d3cff. Chart p.1 "Assess and classify the sick young infant". The WHO 2019 *Management of the sick young infant aged up to 2 months: chart booklet* (https://www.who.int/publications/i/item/9789241516365) could not be downloaded (WHO IRIS blocked). Its thresholds are UNVERIFIED here.

Secondary and qualitative sources (SECONDARY):

9. *Revisiting Community Case Management of Childhood Pneumonia: Perceptions of Caregivers and Grass Root Health Providers in Uttar Pradesh and Bihar, Northern India.* PLOS ONE, 2015. doi:10.1371/journal.pone.0123135. Full text via Europe PMC (PMC4405201), Results section "Local illness terms for pneumonia". Finding: "pneumonia" itself is widely used locally, and local terms focus on chest indrawing rather than fast breathing. The actual term list is on a project website not reached (UNVERIFIED).
10. Kesterton AJ, Cleland J. *Neonatal care in rural Karnataka: healthy and harmful practices, the potential for change.* BMC Pregnancy & Childbirth, 2009. doi:10.1186/1471-2393-9-20. Gives Karnataka (Kanakapura, Kannada) context only; no danger-sign vocabulary.
11. *Qualitative assessment of family caregiver-centered neonatal education program in Karnataka, India.* PLOS Global Public Health, 2023. doi:10.1371/journal.pgph.0000524. Karnataka danger-sign education context; no Kannada lexicon.
12. Vikaspedia (MeitY/C-DAC), *Danger signs during the course of a pregnancy.* https://en.vikaspedia.in/viewcontent/health/women-health/pregnancy-health-1/danger-signs-during-the-course-of-a-pregnancy?lgn=en. SECONDARY; seen only in search snippets. The Kannada version is JS-rendered and could not be read.
13. ACOG Foundation, *Urgent Maternal Warning Signs* (Kannada), V6 May 2026. https://saferbirth.org/wp-content/uploads/urgent_maternal_warning_signs_Kannada.pdf. SECONDARY, non-Indian. Its copyright notice **prohibits use for AI/LLM training or generation**, so no wording from it is used here. Native-speaker reviewers may consult it themselves.

Not reachable or not found: hbnc-hbyc.mohfw.gov.in (connection refused); iec.unicef.in (DNS failure; reportedly hosts Kannada newborn danger-sign leaflets); any Karnataka NHM Kannada ASHA module or Kannada MCP card / "Thayi card".

---

## Risks and open questions (could cause a missed danger sign)

1. **No verified Kannada.** Every Kannada phrase is UNSOURCED-linguistic and in Old-Mysore register. North Karnataka and Hyderabad-Karnataka speech (Dharwad, Kalaburagi), and Dakhni Urdu speakers, will phrase things differently. **Action:** get 2–3 Karnataka ASHAs or an ANM to review the `kn` lists. Look for the Karnataka Kannada MCP card or "Thayi card" and the Kannada ASHA modules from NHM Karnataka or the SIHFW Karnataka training cell.
2. **Negation polarity.** These signs are *expressed* with a negator: `anc_reduced_fetal_movement`, `nb_poor_feeding`, `nb_no_urine_stool`, `pnc_no_urine`, `ch_unable_to_drink`, `nb_weak_cry`, `nb_birth_asphyxia`, `anc_retained_placenta`, `ch_fever_persistent` ("bukhaar nahi utar raha"), and `ch_lethargic_unconscious` ("prajne illa"). Generic negation detection (NegEx-style) would mark them "absent" and **miss the danger sign**. Also, "band ho gaya / nintide" means the sign resolved for bleeding but means danger for fetal movement and feeding. **Action:** keep a per-sign polarity flag, and if unsure, surface the sign to the ASHA instead of dropping it.
3. **Threshold conflicts between official documents.** Newborn fever is 37.2 vs 37.5 °C; newborn hypothermia is 35.5 vs 35.0 °C; postpartum bleeding is ">5 pads/day" vs "2–3 pads in 20–30 min"; child fever persistence is 2 vs 7 days; fast breathing is ">60" vs "≥60". **Recommendation:** fire on the more sensitive value (≥37.2 °C fever; <36.5 °C "cold, warm and recheck" and <35.5 °C refer; ≥60/min; >2 days fever). Get clinical sign-off before the demo states which document governs. The 2026 module is newest, but it is internally inconsistent: it gives a normal range of 36.5–37.5 °C on p.8 and calls fever >37.2 °C on p.28.
4. **Urgency conflicts.** Fever and burning urine in pregnancy, severe anaemia, and umbilical redness are "non-emergency" or "local infection" in M6 and FIMNCI, but "danger sign / immediate" in INT26 or MCP. Several official flows also tell the ASHA to *treat first* (paracetamol, cotrimoxazole, amoxicillin, gentian violet). The app must not echo that. "Refer to PHC" is the only output, so for these signs the app is *more* conservative than the module. Make sure the UI wording ("refer immediately" vs "refer") does not overstate or understate this.
5. **Lexical collisions.** In Hindi, "peela pad gaya" can mean pale/anaemic (mother, per M6HI p.39) or jaundiced (newborn). "Kamzori" and "chakkar" are vague. Kannada "moorchhe" covers fainting and fits; "sadila" (limp) is itself a danger sign. "Fits" may be used loosely for shivering with fever. "Thoda bleeding" (spotting) in pregnancy is still the official sign ("any amount"), so do not downgrade it.
6. **Numbers in speech.** Breath counts, temperatures (°F vs °C, "ek sau do"), pad counts, hours and days decide several thresholds. Mis-parsing "nuraa eradu" (102) or "saath" (60) vs "saat" (7) could miss a sign. See 02-vocab-numbers.md.
7. **Unverified items:** the Hb cut-off for severe anaemia; the retained-placenta time cut-off; the M7 asphyxia and malnutrition page numbers; the exact Hindi wording on the Hindi MCP card and HBNC form; the WHO 2019 young-infant chart (it may change PSBI criteria such as feeding and movement); whether the 28-05-2018 MCP revision changed any wording; and whether "pasli chalna" (chest indrawing) and "dabba" (pneumonia) are attested folk terms. All are marked UNVERIFIED or UNSOURCED in the YAML.
8. **Coverage gaps.** Post-abortion signs (M7 p.37, INT26 p.197) are listed only as a note. INT26 Parts A and C (e.g. emergencies, snakebite, NCDs) were not reviewed. The NHSRC *Emergency Care for FLW – Obstetric and Neonatal Emergencies* (2022) was found but not read and may give extra thresholds: https://www.nhsrcindia.org/sites/default/files/2022-11/Emergency%20Care%20for%20FLW%20-%20Obstetric%20and%20Neonatal%20Emergencies.pdf
