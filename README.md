# ASHA Voice Register: backend core

The safety and language logic from `PLAN.md`, built from the three research files in `research/`. Pure Python, standard library only. No network or LLM calls, so everything runs and is tested without API keys.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest              # 126 tests
.venv/bin/python tools/demo_visit.py    # the PLAN §11 demo visit, as text
.venv/bin/python tools/extract_research.py   # re-copy cited data after research/ changes
```

| File | What it does | From |
|---|---|---|
| `tools/extract_research.py` | Copies the 73 cited signs, 479 phrases, 199-term glossary and 0–100 number tables out of `research/*.md` into `backend/data/`, so cited content is never retyped | 01, 02 |
| `asha/danger.py` | Danger-sign matching with per-sign polarity, the danger-sign receipt, vitals thresholds, safety-turn selection | 01 |
| `asha/numbers.py` | Spoken numbers in Hindi, Kannada and English: fractions, kilo + gram, BP, decimals, IDs, range checks | 02 rules 2–7, 14 |
| `asha/dates.py` | `kal` / `parson` resolved by tense, Kannada relative days, day-only dates, weeks and months as ranges, durations kept as durations | 02 rules 8–13 |
| `asha/verbalize.py` | Numbers, IDs and dates written as words for Timbre | 02 §4c, rule 15 |
| `asha/guard.py` | Last check before speech: blocks drug names, doses, treatment verbs and diagnosis words | PLAN F7 |
| `asha/speak.py` | Fixed templates with typed slots; the AI disclosure must come first | PLAN F7 |
| `asha/readback.py` | Clinically gated read-back: at most one non-safety question, one safety turn of up to 3 signs | PLAN F5 |
| `asha/correction.py` | A correction changes only the named field; danger signs can't be cleared; saving needs "record pakka" + 5 s undo | PLAN F6 |
| `asha/gnani.py` | Prisma headers (validated), keyterm selection (100 Latin / 60 Kannada / 40 Devanagari), exact 1,024-byte frames, Timbre request | 03 |
| `asha/visit.py` | Connects the modules into one turn-by-turn visit | — |

## Danger-sign rules (research/01)

- **Receipt.** Every sign in the visit's group is marked `present`, `ruled_out` (with her words quoted) or `not_checked`. A sign is never recorded as a silent "no".
- **Negation per sign.** For 10 signs the danger phrase itself contains a negator ("doodh nahi pee raha"), so there "nahi" means danger.
- **Resolved is still present.** "Pehle tha, ab nahi" and "band ho gaya" are kept as `present` with a history flag. Hedges ("thoda thoda", "aadru ide") never cancel a sign.
- **A later "no" cannot clear a danger sign.** The sign is marked disputed and left for the ANM.
- **Ruling a sign out needs strong evidence.** Only a full, specific, in-order phrase rules a sign out. A word shared by many signs ("dard") cannot.
- **Fail closed.** `ruled_out` is only recorded in languages listed in `tested_languages` (default `hi`, `en`). Kannada answers stay `not_checked` until the Kannada evaluation passes; then add `"kn"`.
- **Vitals.** BP, temperature, breaths and weight thresholds come from the cited sources. Where two sources conflict, the more sensitive threshold is used.
- **Feet-only swelling.** It is asked about in the safety turn, not flagged as an alert, as the research note says.

## Not built yet

- **Network relays.** The FastAPI WebSocket relays to Prisma and Timbre.
- **LLM steps.** The LLM extractor and the LLM danger classifier (the second check).
- **Storage.** The encrypted store.
- **Evaluation.** The `eval/` harness on recorded clips.
- **Browser mic code.** `web/mic/` from the earlier README isn't in this folder.

## Native-speaker checks needed

All Kannada phrases and templates are UNSOURCED-linguistic, as are the rule-generated Kannada numbers 21–99 and the hundreds combining form. Check them by ear in Timbre before the demo.
