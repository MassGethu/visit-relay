# ASHA Voice Register

**Speak the visit. Never miss a danger sign.**

A voice agent for ASHA workers, India's community health workers. She speaks her home-visit notes in
Hindi, Kannada or English, mixed however she naturally talks. The agent fills in the visit record, alerts
her to danger signs, reads back only the values it's unsure of, and saves the record. An ANM dashboard then
follows every flagged case until it reaches the PHC.

Built for the Gnani Voice Hackathon "Build Bangalore 2.0", PS1 Healthcare. Team CODEFATHER.

> **All data is synthetic.** No real patients are used.

## What makes it different

**Safety first**
- **Two independent danger checks.** A rules check on 73 signs cited from MoHFW/NHSRC sources, plus an
  LLM check. Either one can raise an alert. The alert never waits for the LLM, so it still fires when the
  LLM is slow or offline.
- **A danger sign can't be erased.** A later "no" marks the sign as disputed for the ANM. Signs nobody
  discussed are recorded as "Not checked", never as "No".
- **Every alert shows its source,** for example *GOI MCP Card, Antenatal: vaginal bleeding in pregnancy*.
- **Never acts as a doctor.** The LLM only returns JSON. Everything spoken comes from fixed templates, and a
  guard blocks drug names, doses and diagnosis words before anything is spoken. The only advice it gives is
  "refer to PHC".
- **Says it's an AI** in the first sentence of every session, in her language.

**Fits how she works**
- **Handles code-mixed speech** in Hindi, Kannada and English, using Gnani Prisma's codemix mode.
- **Reads back only doubtful values:** *"28 ya 2.8 kilo? Sahi bataiye."*
- **Catches self-corrections.** "2.6… nahi, 2.8" saves 2.8 and keeps her exact words as evidence.
- **Safety question:** "You didn't mention these:" followed by up to 3 key signs she skipped.
- **Voice commands:** "record pakka" saves, "ruko" undoes within 5 s, and "dheere" turns on discreet mode.
- **Hands-free:** waits for her spoken finish cue instead of a button press.

**Built for the field**
- **Works offline.** The page loads from a service worker, and recordings are kept encrypted in IndexedDB
  until they sync.
- **Fast:** audio streams both ways, with a target of under 1.5 s to the first reply.
- **Private:** records are encrypted at rest, and `scripts/delete_all.py` wipes them all.

**Closes the loop**
- **ANM dashboard:** search patients, see what's due, overdue or flagged, and move each referral through
  Flagged → Referred → Reached PHC → Closed.

## How it works

```
Phone (web/index.html)                     FastAPI (backend/app.py)                 Gnani
 mic → AudioWorklet → 16 kHz PCM, 1024 B ─WS /ws─▶ relay ───────────────────────▶ Prisma v3.0 (STT)
                                                    │ transcript
                                                    ▼
                                           Visit (backend/asha/visit.py)
                                           rules danger check ─┐
                                           LLM (Groq → Gemini → Ollama) JSON ─┤→ record, alerts, receipt
                                           templates + guard ──┘
 speaker ◀── 24 kHz PCM + JSON events ◀─WS── relay ◀──────────────────────────── Timbre v3.0 (TTS)
 cards.js draws record / alert / receipt

Laptop (web/dashboard.html) ◀── REST /api/dashboard, /api/patients/…, /api/referrals ── encrypted store
```

- **Phone page:** plain JavaScript with no framework. `mic-worklet.js` downsamples to 16 kHz and cuts
  exact 1,024-byte frames. `audio-player.js` plays the streamed TTS and stops it on barge-in. `cards.js` draws
  every backend event through `window.Cards.handle(event)`. `i18n.js` translates the page into hi, kn or en.
- **Relay:** browsers can't set WebSocket headers, so the phone connects to our server and the server
  connects to Gnani.
- **LLM:** Groq first (JSON mode, 3 s timeout), then Gemini Flash-Lite, then local Ollama. If all of them
  fail, the visit continues with rules only. The system prompt is in `prompts/understand.md`.
- **Dashboard:** a single-page app with views in the URL, so links and the back button work. It is
  search-first and never lists every patient.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn websockets httpx cryptography pytest
cp .env.example .env        # fill GNANI_API_KEY, GROQ_API_KEY, DB_KEY (optional: GEMINI_API_KEY, OLLAMA_URL, LOCAL_MODEL)
.venv/bin/python scripts/seed_visits.py     # synthetic visits for the dashboard
.venv/bin/python -m uvicorn app:app --app-dir backend --port 8791
```

- Phone page: `http://localhost:8791/`. A phone needs HTTPS for the mic, for example with
  `cloudflared tunnel --url http://localhost:8791`.
- Dashboard: `http://localhost:8791/dashboard.html`

Other commands:

```bash
.venv/bin/python -m pytest -q                 # 520 tests
.venv/bin/python tools/demo_visit.py          # text-only demo visit, no keys needed
.venv/bin/python tools/extract_research.py    # re-copy cited data after research/ changes
.venv/bin/python scripts/latency_report.py    # latency summary from eval/latency.csv
.venv/bin/python scripts/delete_all.py --yes  # wipe all stored records
```

## Code map

| Path | What it does |
|---|---|
| `web/index.html`, `app.js`, `mic-worklet.js`, `audio-player.js` | Phone page: mic, streaming, playback, talk button |
| `web/cards.js`, `cards.css` | Screen cards: record, danger alert, read-back, receipt, saved |
| `web/offline-visit.js`, `visit-worker.js` | Offline: encrypted IndexedDB queue and service-worker cache |
| `web/dashboard.html`, `dashboard.js`, `dashboard.css` | ANM / supervisor dashboard |
| `web/i18n.js` | Hindi / Kannada / English page text |
| `backend/app.py` | FastAPI: WebSocket relay, REST APIs, static files |
| `backend/llm.py`, `prompts/` | LLM understanding: one sentence in, validated JSON patch out |
| `backend/store.py` | Encrypted record store |
| `asha/danger.py` | Danger-sign matching with per-sign polarity, receipt, vitals thresholds |
| `asha/numbers.py`, `dates.py`, `verbalize.py` | Spoken numbers and dates in three languages, and the reverse for TTS |
| `asha/guard.py`, `speak.py` | Fixed speech templates and the drug / dose / diagnosis guard |
| `asha/readback.py`, `correction.py` | Read-back of doubtful values, corrections, save and undo |
| `asha/gnani.py` | Prisma headers, keyterms, 1,024-byte frames, Timbre request |
| `asha/visit.py` | Connects the modules into one turn-by-turn visit |
| `asha/dashboard.py`, `beneficiary.py` | Dashboard views and beneficiary ID matching |
| `backend/data/` | Cited danger signs, lexicon, glossary, number tables, synthetic beneficiaries |
| `research/` | Source of truth for every sign, phrase, number rule and Gnani setting |

## Danger-sign rules (research/01)

- **Receipt.** Every sign in the visit's group is marked `present`, `ruled_out` (with her words quoted) or
  `not_checked`. A sign is never recorded as a silent "no".
- **Negation per sign.** For 10 signs the danger phrase itself contains a negation ("doodh nahi pee raha"),
  so there "nahi" means danger.
- **Resolved is still present.** "Pehle tha, ab nahi" stays `present` with a history flag. Hedges ("thoda
  thoda") never cancel a sign.
- **Ruling a sign out needs strong evidence.** Only a full, specific phrase rules a sign out. A shared word
  like "dard" can't.
- **Fail closed.** `ruled_out` is recorded only in tested languages (`hi`, `en`). Kannada answers stay
  `not_checked` until the Kannada evaluation passes.
- **Vitals.** Thresholds come from the cited sources. Where two sources conflict, the more sensitive
  threshold is used.

## Responsible AI

- The AI disclosure comes first in every session. The agent never diagnoses, never names a medicine and
  never gives a dose.
- API keys live only in `.env`, which is gitignored. Only synthetic data is used, records are encrypted at
  rest, and there is a one-command wipe.
- Kannada phrases and templates still need a native-speaker check by ear in Timbre.
