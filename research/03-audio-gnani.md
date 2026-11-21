# 03 — Browser audio front-end and Gnani Prisma v3.0 / Timbre v3.0

Accessed 2026-11-13. Every claim has a source tag `[Sn]` that points to the Sources list. Vendor and blog sources are marked SECONDARY there. "UNVERIFIED" means no source was found that settles the point.

Current client chain (given): getUserMedia → AudioWorklet → 80 Hz 4th-order HPF → own slow AGC (max +12 dB) → soft limiter → energy VAD on the 300–3400 Hz band → resample to 16 kHz → WebSocket → Gnani Prisma v3.0. Replies come from Gnani Timbre v3.0.

---

## Summary

- **Do not add a neural or spectral denoiser (RNNoise, DeepFilterNet, Speex, browser `noiseSuppression`) in front of Prisma by default.** Every ASR vendor checked (Google, Deepgram, AssemblyAI) advises against it. In recent studies, denoising raised WER on Whisper-class models, including on noisy Bengali speech [S9][S10][S11][S12][S13][S14][S15]. RNNoise's author calls denoise-then-ASR "sub-optimal" [S16]. Keep a denoiser only as an A/B arm, or use it only to drive our own VAD, never on the audio sent to Prisma.
- **On Chrome for Android, "browser processing" means two different things.** Echo cancellation comes from the platform (VOICE_COMMUNICATION input preset, vendor DSP or HAL) whenever the device reports an AcousticEchoCanceler. Noise suppression and AGC run in WebRTC's software APM: NS at level `kHigh`, and AGC as a *fixed* +6 dB digital gain [S1][S2][S3][S4][S5]. Turning echo cancellation off switches the input preset, and on some devices that has given quiet or near-silent audio [S2][S7][S8].
- **Gnani gives us cheaper levers than DSP**: server VAD headers (`x-vad-threshold`, `x-min-speech-ms`, `x-min-silence-ms`, `x-min-segment-ms`), `language_code` hints (1–4 languages, for example `hi-IN,en-IN`), `keyterms` (≤200), `topic` (≤1,600 chars), `speaker_names` (1–4), plus `commit` and `update_settings` frames [S20][S21]. Gnani's own (SECONDARY) numbers: keyterms raised term recall from 70.9% to 90.3%, and language hints cut Hindi-English call WER from 34.14 to 18.93 [S24].
- **Prisma streaming has strict framing**: exactly 1,024-byte frames (512 samples) every 32 ms at 16 kHz, with no bursting. A browser WebSocket cannot set the required headers, so a backend proxy is mandatory [S21].
- **Timbre v3.0** has 13 voices, and each speaks all 10 languages. `<pauses>` takes **no duration**. Speed range is 0.85–1.15. There is **no documented cancel message**. Barge-in works by closing the WebSocket, which is what Gnani's own Pipecat plugin does [S25][S26][S27][S29].

---

## 1. Browser audio processing on Chrome for Android

### 1.1 What Chrome actually does (from Chromium source, `main` branch, read 2026-11-13)

| Feature | What happens on Android | Source |
|---|---|---|
| Echo cancellation | `AudioManagerAndroid::GetInputStreamParameters` sets the `ECHO_CANCELLER` platform-effect flag only if the Java side reports `AcousticEchoCanceler` as available. If it is set, Blink's `EchoCanceller::GetPreferredAec` returns `kPlatformProvided` (the platform/vendor AEC is used, not WebRTC AEC3). If it is not set, Chrome falls back to its software AEC. | [S2] lines ~731-738; [S5] `GetPreferredAec` |
| Input preset | AAudio path: `AAUDIO_INPUT_PRESET_VOICE_COMMUNICATION` when AEC is needed, otherwise `AAUDIO_INPUT_PRESET_GENERIC` (or CAMCORDER behind a rollback flag). Chromium comment: they avoid `UNPROCESSED` "because the lack of automatic gain control results in quiet, sometimes silent, streams." Legacy OpenSL ES path: VOICE_COMMUNICATION with effects, CAMCORDER without. | [S3] lines ~511-529; [S4] lines ~247-251 |
| Communication mode | When effects are not `NO_EFFECTS`, Chrome sets the Android audio mode to `MODE_IN_COMMUNICATION`. | [S2] `MakeAudioInputStream` |
| Noise suppression | Software WebRTC APM: `apm_config.noise_suppression.enabled = settings.noise_suppression`, level `kHigh`. | [S1] `media/webrtc/helpers.cc` |
| AGC | Software WebRTC APM. On Android, AGC1 is off and AGC2 runs with **fixed digital gain 6 dB**, adaptive digital off, input-volume controller off. On desktop, AGC2 is adaptive. | [S1] `ConfigAutomaticGainControl` |
| Known-bad chips | Chrome disables AAudio input on Unisoc ("ums" board) devices on Android 11 and below "due to missing/broken echo cancellation" (crbug 344607452). | [S2] `UseAAudioInput()` |

**What this means:**
- `noiseSuppression:false` and `autoGainControl:false` switch off Chrome's *software* NS and AGC. Our AGC already does more than Chrome's fixed +6 dB, so Chrome's AGC adds little.
- `echoCancellation:true` usually means the vendor's VOICE_COMMUNICATION chain. AOSP's own example config applies **AEC + NS** to `voice_communication`, and says the NS for that source is "tuned for stationary noise" [S6]. So with AEC on, a vendor NS may run whatever our `noiseSuppression` constraint says. This is an inference from [S2][S3][S6]. Whether a given phone does this depends on its `/vendor/etc/audio_effects.xml`, so it is UNVERIFIED per device.
- AOSP forbids NS by default on the `VOICE_RECOGNITION` source, which is Android's own ASR path [S6]. Chrome never uses `VOICE_RECOGNITION` [S3][S4].

### 1.2 Do low-end devices use hardware DSP?
UNVERIFIED in general. Android 10+ says devices "should" provide an AEC on VOICE_COMMUNICATION capture and, if they do, expose it via `AcousticEchoCanceler` [S6]. Whether that runs on a DSP or the CPU is vendor-specific and not documented. Concrete low-end evidence: the Unisoc exclusion above [S2], and a Samsung developer forum thread titled "Built-in AEC cancels human voice" [S7a] (SECONDARY, not read in full).

### 1.3 Cases where constraints are ignored or behave unexpectedly
- Setting `echoCancellation:false` on Chrome Android gave "low or inaudible sound". Pipe fixed it by leaving `echoCancellation` at the default (true) [S8] (SECONDARY, 2022). This matches the Chromium comment on quiet streams without platform AGC [S3].
- A Stack Overflow report says audible processing remains even with `echoCancellation`/`autoGainControl` `{exact:false}` on Chrome Android [S7] (SECONDARY, 2019; it may predate the current AAudio path).
- Always read `track.getSettings()` after capture to log what was actually applied. Chrome reports the AEC type there [S30] (SECONDARY blog by Chrome team, 2018).

### 1.4 Vendor guidance on NS, AGC and AEC before ASR
| Vendor | Guidance | Source |
|---|---|---|
| Google Cloud STT | "All noise reduction processing should be disabled"; "Don't use automatic gain control (AGC)"; "Avoid audio clipping"; the recognizer is "designed to ignore background voices and noise without additional noise-canceling." | [S9] SECONDARY (vendor docs) |
| Deepgram | For transcription, "skip noise suppression and send unaltered audio". For voice agents, use platform-native AEC and add NS only if false barge-ins persist. Higher suppression "increases the risk of clipping speech". The example uses `echoCancellation:true, noiseSuppression:false`. | [S10] SECONDARY |
| AssemblyAI | "we recommend applying noise reduction for playback purposes only, not before transcription." | [S11] SECONDARY |
| Corti (medical STT) | **Disagrees in part.** Dictation: AEC off, AGC off, NS "Mild (-15dB)". Ambient conversation: AEC on, AGC on, NS mild. Target about -12 dBFS RMS with peaks near -3 dBFS. | [S31] SECONDARY |

No public measurement was found of Chrome's WebRTC NS (`kHigh`) specifically changing WER. UNVERIFIED.

---

## 2. RNNoise, DeepFilterNet, Speex and similar before modern ASR

### 2.1 Evidence on WER
| Study | Setup | Result | Source |
|---|---|---|---|
| Islam, Nahar, Hamid 2026 (arXiv 2603.04710) | SAM-Audio (Small) separation, then Whisper tiny to large-v3, zero-shot. **Bengali** BanglaYTV (929 noisy real-world clips) and English MS-SNSD | WER and CER rose in **every** model-dataset pair. Bengali large-v3: WER 0.6583 → 0.7735, CER 0.2413 → 0.3474 (Tables I–IV) | [S12] |
| Chondhekar et al. 2025 (arXiv 2512.17562) | MetricGAN+ denoising, then Whisper, Parakeet, Gemini Flash 2.0, Parrotlet-a; 500 medical recordings | Noisy input beat enhanced input in all 40 configurations; +1.1 to +46.6 absolute semWER (abstract). The dataset language is not stated on the abstract page | [S13] |
| Iwamoto et al. 2022 (arXiv 2201.06685, Interspeech 2022) | Decomposes SE errors | Artifacts, not residual noise, are the main cause of ASR degradation. Remedy: "observation adding", which mixes the noisy input back in | [S14] |
| Huo, Zhang, Zhang 2026 (arXiv 2607.11157) | Several STFT-mask enhancers, then wav2vec 2.0 and Whisper | Most enhanced outputs had higher WER than the noisy input. For Whisper, only a mild correction helped; stronger correction raised WER | [S15] |
| Sapeha et al. 2026 (ICAIIT, DOI 10.25673/123832) | DeepFilterNet 0.5.6, then faster-whisper large-v3 or wav2vec2, car noise | DeepFilterNet "neutral to slightly adverse" for faster-whisper, helpful for wav2vec2 at low SNR | [S17] |
| Braun & Gamper 2021 (Microsoft Research) | DNN NS losses | Distortion and artifacts "often significantly degrade" ASR | [S18] |
| AudioLab.tools 2026 (SECONDARY, n = 24 sentences per condition) | RNNoise (ffmpeg `arnndn`), then Whisper small and large-v3-turbo | No harm on clean or telephone-band audio. Street noise: small +3.7 WER points. Restaurant noise at -5 dB: small +8.9, turbo +5.3. "did not clearly help anywhere" | [S19] |
| DeepFilterNet issue #483 (SECONDARY, user report) | DeepFilterNet, then Whisper and Seamless on FLEURS | About 20% worse WER on both clean and noise-augmented audio | [S20a] |
| Valin (RNNoise author), 2017 | — | RNNoise targets real-time communication, not ASR. Simply denoising before ASR is "sub-optimal" | [S16] |

**Indian-language or telephone evidence:** only [S12] (Bengali, Whisper) and [S19] (telephone band, English) were found. **No study was found on Prisma, or on Hindi, Kannada, Tamil or Telugu with RNNoise or DeepFilterNet.** UNVERIFIED. Gnani's own benchmark method sends audio "with no enhancement or pre-processing" [S23] (SECONDARY). Gnani says Prisma v3.0 was trained and evaluated on six real telephony codecs [S24] (SECONDARY). Together these suggest the model expects raw, noisy input.

Speex preprocessor: no ASR study found. UNVERIFIED. It is a classical spectral suppressor, the family that [S14][S18] say produces the artifacts that hurt ASR. That is an inference.

### 2.2 CPU cost on low-end ARM
| Model | Published cost | Source |
|---|---|---|
| RNNoise | About 60x real-time on x86; about 7x real-time on a Raspberry Pi 3 (Cortex-A53) before vectorization, i.e. roughly 14% of one A53 core (derived). Operates at 48 kHz; 10 ms look-ahead | [S16], [S22] |
| DeepFilterNet2 | RTF 0.04 on a notebook Core-i5. No ARM figure | [S32] |
| DeepFilterNet3 | RTF 0.19 single-threaded on a notebook CPU. No ARM figure | [S33] |
| `@sapphi-red/web-noise-suppressor` 0.4.1 (2026-09-19) | AudioWorklet nodes: NoiseGate, RNNoise (shiguredo/rnnoise-wasm), Speex preprocess, GTCRN. No CPU figures published | [S34] |

No published measurement exists for WASM RNNoise or DeepFilterNet on low-end Android (e.g. Cortex-A53 or Unisoc). UNVERIFIED. Measure it in our A/B with `performance.now()` per worklet block.

---

## 3. Measured effects of HPF, AGC and limiting on WER

| Stage | Evidence | Verdict |
|---|---|---|
| **80 Hz high-pass** | No ASR study measuring an 80–100 Hz HPF on WER was found. The search returned only human-listener studies at 1 kHz+ cutoffs (not relevant). UNVERIFIED. Indirect: WebRTC's own APM pipeline, which every WebRTC client already sends to ASR vendors, includes a high-pass stage (not verified in source in this pass, so UNVERIFIED). Gnani's model is trained on 8 kHz telephony codecs [S24], and those are band-limited above 300 Hz in narrowband, so energy below 80 Hz is unlikely to carry information the model uses. That is an inference. | Keep. Low risk, near-zero CPU. Not worth an A/B arm. |
| **AGC** | Google: "Don't use automatic gain control (AGC)" [S9]. Corti: AGC on for conversation, off for dictation [S31]. **Sources disagree.** No WER measurement found. Chrome's Android AGC is only a fixed +6 dB [S1]. Risk of a slow AGC: it lifts noise floors between words. Benefit: quiet or distant speakers reach the model's operating level. | A/B: our AGC on vs off (fixed gain only). |
| **Clipping / limiter** | Clipping measurably degrades ASR. Maymon et al. (Interspeech 2013) got >4% relative WER reduction by *restoring* clipped speech with >0.5% clipped samples [S35]. Tachioka et al. relate clipping level to ASR performance (Acoustical Science & Technology 35(6), 2014) [S36]. Google: "Avoid audio clipping" [S9]. No study of a *soft limiter's* own effect on WER was found. UNVERIFIED. | Keep the limiter as a safety net, but set it so it rarely engages (target about -12 dBFS RMS, peaks below -3 dBFS, per [S31]). Log the engage rate. |
| **Client energy VAD gating** | Deepgram: noise suppression or gating "clips the first words of utterances and disproportionately affects short responses" [S10]. Gnani runs its own server VAD and wants continuous real-time frames ("Do not buffer and burst; this degrades VAD accuracy") [S21]. | A/B: stream continuously and let Gnani's VAD segment, vs our gate (with ≥300 ms pre-roll). |

---

## 4. Gnani specifics

### 4.1 Prisma v3.0 (STT)
- **Release:** 22 Oct 2026. Opt-in with `model: prisma-v3.0`; the default is still v2.5 [S28][S20].
- **Languages:** bn, en, gu, hi, kn, ml, mr, pa, ta, te (`-IN`) plus `indic-auto`. Up to 4 hints, for example `hi-IN,en-IN`. These are "a hint, not a lock" [S20].
- **Code-mix:** `format` is one of `verbatim | transcribe | codemix | transliterate`. On streaming the default depends on `language_code`: for a single `hi-IN`/`en-IN` it is `transcribe`, otherwise `verbatim` [S20][S21]. `detected_language_code` is per utterance, derived from the script. It stays the native tag while native-script letters are ≥30% [S20]. Hindi and Marathi short utterances may be tagged `hi-IN` [S20].
- **Noise:** the only noise numbers are vendor claims. False text on noise-only audio fell from 13.4% (v2.5) to 4.2% (v3.0). The model was trained and evaluated on six telephony codecs at native 8 kHz [S24] (SECONDARY). No WER-on-noisy-speech figure exists for v3.0. UNVERIFIED.
- **Accuracy (vendor):** Vistaar macro WER 16.9 vs ElevenLabs Scribe v2 19.98, Azure 20.51, Deepgram Nova 3 26.57 [S24][S37]. **Sources disagree on a detail:** CXOToday says v3.0 had the lower WER on each of the seven Vistaar datasets [S37]. ArtRealmAI says Azure beat it on MUCS [S38]. Both are SECONDARY.
- **Context fields** [S20]:
  - `keyterms`: up to 200 words or short phrases; JSON array or CSV; mixed scripts OK. In streaming headers, non-ASCII must be JSON-escaped (`\uXXXX`). An unspoken keyterm "should not appear in the output". More than 200 → `400 INVALID_CONTEXT` on REST; on streaming "an invalid value is ignored" [S21]. Can be replaced mid-session via `{"type":"update_settings","bias":{"list":[...]}}`; it applies from the next utterance [S21]. `bias_score` is ignored on v3.0.
  - `topic`: any non-empty text up to 1,600 chars (REST/Realtime; Batch needs 30–1,600). Fixed for the session on streaming.
  - `speaker_names`: 1–4 names, fixed for the session. This is **not** diarization; it only helps spelling. "Unspoken speaker names were never inserted into the transcript."
  - `previous_text`: last 600 chars kept.
  - Values containing `<|` or `|>` are rejected.
  - Effect (Gnani's own test, 60 public clips per combination): "every combination that included `keyterms` was more accurate than no context and none was worse." Warning from the same page: a model can become **less** accurate with context, so compare on your own audio.
  - **Docs disagree on streaming support:** the changelog says "Realtime accepts `keyterms` only (`x-keyterms`)" [S28]. The Prisma v3.0 page and the Realtime page say all four are accepted as headers [S20][S21]. The Limits page labels `previous_text` "REST only" [S22b]. Test `topic` and `speaker_names` on our WebSocket and confirm they take effect.
- **Streaming protocol** [S21]:
  - `x-sample-rate` must be 8000, 16000, 44100 or 48000.
  - Frames are exactly 1,024 bytes (512 samples, 32 ms at 16 kHz) at real-time cadence.
  - `x-idle-timeout-sec` 5–900 (default 60). Session cap is 15 min (close code 1001).
  - `{"type":"commit"}` force-closes the current utterance.
  - VAD headers are fixed per connection:
    - `x-vad-threshold`: default 0.7; clean mic 0.45–0.55, telephony 0.65–0.75.
    - `x-min-silence-ms`: default 500, range 100–2000.
    - `x-min-speech-ms`: default 100, range 50–2000; "Raise in noisy environments".
    - `x-min-segment-ms`: default 120, range 100–1000; raising it too far "silently drops short answers".
    - `x-max-speech-s`: 5–120, off by default.
  - **Browser WebSocket cannot set custom headers, so proxy through your backend** [S21].
- **What v3.0 does not do:** word timestamps, diarization (REST/Realtime), translation, token-by-token streaming [S20].

### 4.2 Timbre v3.0 (TTS)
- **Voices (13, all speak all 10 languages)** [S25]:
  - Female: **Shivani, Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika**
  - Male: **Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad**
  - Gnani describes Chetana as "Gentle, empathetic voice for healthcare and telecom customer service". Shivani is "Warm, patient, empathy-first". Yashraj is a "Warm narrative voice for e-learning and IVR narration".
  - Timbre v2.5 voices (e.g. Nalini) are rejected with `400` on v3.0.
  - Pipecat and LiveKit default to `Avinash` on v3.0 [S27][S29].
- **Languages:** hi, en, ta, te, kn, ml, mr, pa, bn, gu, plus `auto`. `hi-en` (Hinglish) is listed for the endpoint [S26]. Whether `hi-en` is valid with v3.0 is not stated. UNVERIFIED.
- **Speed:** 0.85 to 1.15, or `"slow"`/`"medium"`/`"fast"` = 0.85/1.0/1.15 [S26]. The REST error table notes "the allowed range depends on the model", but only one range is published. UNVERIFIED whether v3.0 differs.
- **Audio tags** [S39][S25]:
  - Syntax is `<tag>` inline. Tags are case-sensitive, with no closing tag. A tag applies from its position to the end of the input or until the next tag. Unknown tags are stripped silently.
  - The 13 tags: `<laugh> <giggle> <sigh> <exhales> <sniffles> <yawns> <coughs> <clears throat> <whispers> <shouting> <excited> <slow> <pauses>`.
  - **`<pauses>` takes no duration parameter.** It is a "Short silence — not spoken aloud". No duration syntax is documented anywhere. For a longer pause, repeating the tag is UNVERIFIED.
  - Tags count as billable characters.
  - Gnani tip: `<pauses>` before a prompt "gives callers time to respond and improves recognition accuracy".
- **Cancel mid-utterance:** the WebSocket TTS protocol documents only `start`, `audio`, `complete` and `error` server messages, and no client cancel or flush message [S26]. "Either side closes — client or server may close the connection at any time." Gnani's Pipecat plugin (`pipecat-gnani` 0.6.0, `tts.py`) implements barge-in by `_disconnect()` then `_connect()`: "so the server stops streaming the interrupted reply" [S27b]. The Python SDK opens a new WebSocket per `synthesize()` call [S40]. **So cancelling means closing the socket (and discarding queued audio client-side), then reconnecting.** Note: `container=ogg` delivers everything as one chunk after synthesis, so use `raw`/`wav` PCM for streaming [S26].

---

## Recommendation table

| Technique | Evidence for | Evidence against | CPU cost | Recommend for our A/B test |
|---|---|---|---|---|
| Browser `noiseSuppression:true` (WebRTC NS kHigh) | Corti suggests mild NS [S31] | Google, Deepgram, AssemblyAI say disable [S9][S10][S11]; enhancement artifacts hurt ASR [S14][S18] | Low (native) | **Yes** (as the "off" baseline vs on; expect off to win) |
| Browser `autoGainControl:true` | Corti: on for conversation [S31] | Google: don't use AGC [S9]; on Android it is only a fixed +6 dB [S1] and duplicates ours | Negligible | **No** (keep off; our AGC covers it) |
| Browser `echoCancellation:true` (platform AEC) | Needed if the mic stays open during TTS; off can give quiet or silent audio on Android [S3][S8]; Deepgram: use platform AEC [S10] | May bring vendor NS on VOICE_COMMUNICATION [S6]; broken on some Unisoc [S2]; MODE_IN_COMMUNICATION [S2] | Free (platform) | **Yes** (true vs false, logging `getSettings()` and RMS) |
| RNNoise (WASM) on the ASR path | Ran without harm on clean or telephone-band audio [S19] | No help, or worse, in noise [S19]; author: "sub-optimal" for ASR [S16]; general SE evidence [S12][S13][S15] | About 14% of an A53 core natively (derived [S16]); WASM on low-end Android UNVERIFIED | **Yes, one arm only**, or better: RNNoise feeding *only our VAD*, with raw audio to Prisma |
| DeepFilterNet | Helps weak models (wav2vec2) at low SNR [S17] | Neutral or worse for Whisper-class [S17]; about 20% worse WER report [S20a] | RTF 0.04–0.19 on a laptop [S32][S33]; too heavy for low-end ARM (UNVERIFIED) | **No** |
| Speex preprocess | None found for ASR | Classical spectral NS, the artifact class [S14][S18] (inference) | Low | **No** |
| 80 Hz 4th-order HPF | Removes rumble or handling noise; telephony-trained model [S24] (inference) | No WER study found (UNVERIFIED) | Negligible | **No** (keep as is; not worth an arm) |
| Our slow AGC (max +12 dB) | Fixes quiet or distant speakers; Corti targets -12 dBFS RMS [S31] | Google: no AGC [S9]; raises the noise floor in pauses (inference) | Negligible | **Yes** (AGC vs fixed gain) |
| Soft limiter | Clipping hurts ASR [S35][S36][S9] | Its own nonlinearity is unmeasured (UNVERIFIED) | Negligible | **No** (keep, tuned to rarely engage; log engage rate) |
| Client VAD gating vs continuous streaming | Saves bandwidth | Gating clips onsets and short answers [S10]; Gnani needs real-time continuous frames [S21] | Negligible | **Yes** |
| Gnani VAD headers (threshold 0.55 vs 0.7, min-speech 100 vs 200 ms, min-silence 500 vs 800 ms) | Documented knobs for noise and false triggers [S21] | Higher threshold may miss soft speech [S21] | Server-side | **Yes** |
| `language_code` hint `hi-IN,en-IN` (or the state language + en) vs `indic-auto` | Vendor: hints cut code-mix WER from 34.14 to 18.93 [S24]; help on short clips and Hindi/Marathi [S20] | Vendor-only numbers | None | **Yes** |
| `keyterms` (ASHA vocabulary: ANC, PNC, IFA, ORS, HBNC, JSY, vaccine names, village names) | Recall 70.9 → 90.3% (vendor) [S24]; no combination worse [S20] | "can become less accurate" warning [S20] | None | **Yes** |
| `topic` / `speaker_names` | Same Gnani test [S20] | Streaming support contradicted in docs [S28] | None | **Yes** (after verifying it is accepted) |
| Timbre `<pauses>` before questions | Gnani tip: improves recognition of replies [S39] | Vendor claim only | None | **Yes** (UX arm, low priority) |

---

## Gnani facts table

| Setting | Value / limit | Source |
|---|---|---|
| STT model id | `prisma-v3.0` (header `model` or legacy `x-model`); default is v2.5 | [S20][S21] |
| STT WS endpoint | `WS /stt/v3/stream` (host `api.vachana.ai`) | [S20] |
| `language_code` | `indic-auto` or 1–4 of bn/en/gu/hi/kn/ml/mr/pa/ta/te-IN | [S20] |
| `format` | verbatim / transcribe / codemix / transliterate; switchable via `update_settings` | [S20][S21] |
| `keyterms` | ≤200 words/phrases; JSON-escape non-ASCII in headers; changeable mid-session via `bias.list` | [S20][S21] |
| `topic` | ≤1,600 chars (Batch 30–1,600); fixed per session | [S20][S21] |
| `speaker_names` | 1–4 names; fixed per session; not diarization | [S20][S21] |
| `previous_text` | last 600 chars kept; "REST only" per Limits page (conflicts with [S21]) | [S20][S22b] |
| Context on streaming | All 4 as headers [S20][S21] vs "keyterms only" [S28]: **conflict** | [S20][S21][S28] |
| Audio framing | PCM16 LE mono, 1,024-byte frames, 32 ms at 16 kHz, real-time cadence | [S21] |
| `x-sample-rate` | 8000 / 16000 / 44100 / 48000 (default 16000) | [S21] |
| `x-vad-threshold` | 0.0–1.0, default 0.7 | [S21] |
| `x-min-silence-ms` | 100–2000, default 500 | [S21] |
| `x-min-speech-ms` | 50–2000, default 100 (200 at 8 kHz) | [S21] |
| `x-min-segment-ms` | 100–1000, default 120 | [S21] |
| `x-max-speech-s` | 5–120, off by default | [S21] |
| `x-idle-timeout-sec` | 5–900, default 60 | [S21][S22b] |
| Session length | 15 min max (close 1001) | [S21][S22b] |
| `commit` frame | Closes the open utterance immediately | [S21] |
| Browser auth | Browser WS cannot set headers, so a backend proxy is required | [S21] |
| TTS model id | `timbre-v3.0` | [S26] |
| TTS WS endpoint | `wss://api.vachana.ai/api/v1/tts`; one request at a time | [S26] |
| Timbre v3.0 voices | F: Shivani, Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika. M: Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad | [S25] |
| TTS languages | 10 (hi, en, ta, te, kn, ml, mr, pa, bn, gu) + `auto`; every v3.0 voice speaks all | [S25][S26] |
| `speed` | 0.85–1.15; "slow"/"medium"/"fast" | [S26] |
| Audio tags | 13 tags, `<tag>` syntax, case-sensitive, no closing tag, unknown stripped, billable | [S39] |
| `<pauses>` | Short silence; **no duration parameter documented** | [S39][S25] |
| TTS sample rates | 8000, 16000, 22050, 24000, 44100, 48000 (default 48000) | [S26] |
| TTS cancel | No cancel message documented; close the WS (Pipecat does disconnect + reconnect) | [S26][S27b] |
| Ogg output | One chunk after synthesis completes (not streamable) | [S26] |

---

## Sources

Chromium source was read from `chromium.googlesource.com/chromium/src/+/main/...` on 2026-11-13. Line numbers are as of that read.

- [S1] Chromium Authors, `media/webrtc/helpers.cc` (`ConfigAutomaticGainControl`, `CreateWebRtcAudioProcessingModule`), 2026. https://chromium.googlesource.com/chromium/src/+/main/media/webrtc/helpers.cc
- [S2] Chromium Authors, `media/audio/android/audio_manager_android.cc` (`UseAAudioInput`, `GetInputStreamParameters`, `MakeAudioInputStream`), 2026. https://chromium.googlesource.com/chromium/src/+/main/media/audio/android/audio_manager_android.cc
- [S3] Chromium Authors, `media/audio/android/aaudio_stream_wrapper.cc` (input preset selection, ~L511–529), 2026. https://chromium.googlesource.com/chromium/src/+/main/media/audio/android/aaudio_stream_wrapper.cc
- [S4] Chromium Authors, `media/audio/android/opensles_input.cc` (~L247–251), 2026. https://chromium.googlesource.com/chromium/src/+/main/media/audio/android/opensles_input.cc
- [S5] Chromium Authors, `third_party/blink/renderer/platform/mediastream/media_stream_audio_processor_options.cc` (`EchoCanceller::GetPreferredAec`), 2026. https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/renderer/platform/mediastream/media_stream_audio_processor_options.cc
- [S6] Android Open Source Project, "Configure preprocessing effects", last updated 2026-10-09. https://source.android.com/docs/core/audio/implement-pre-processing
- [S7] Stack Overflow, "How do I read pure raw mic data in Chrome in Android?", 2019. SECONDARY. https://stackoverflow.com/questions/54050249
- [S7a] Samsung Developer Forum, "Built-in AEC cancels human voice — how to configure correctly?", n.d. SECONDARY (title only seen). https://forum.developer.samsung.com/t/built-in-aec-cancels-human-voice-how-to-configure-correctly/41426
- [S8] Remus (Pipe / addpipe.com), "Fixed issue with HTML5 desktop recorder producing low or inaudible sound when used inline in Chrome on Android", 2022-01-17. SECONDARY. https://addpipe.com/docs/changelog/fixed-issue-with-html5-desktop-recorder-producing-low-or-inaudible-sound-when-used-inline-in-chrome-on-android-219176/
- [S9] Google Cloud, "Best practices: provide speech data" (sections: Sampling rate; Audio preprocessing), n.d. SECONDARY (vendor). https://docs.cloud.google.com/speech-to-text/docs/best-practices-provide-speech-data ; also https://docs.cloud.google.com/speech-to-text/docs/best-practices
- [S10] Deepgram, "Audio preprocessing & barge-in" (sections: Noise Suppression; Echo Cancellation), n.d. SECONDARY. https://developers.deepgram.com/guides/deep-dives/audio-preprocessing-barge-in ; see also Deepgram blog "The noise reduction paradox", SECONDARY, https://deepgram.com/blog/the-noise-reduction-paradox-why-it-may-hurt-speech-to-text-accuracy
- [S11] AssemblyAI, "What are the recommended options for audio noise reduction?" (FAQ note), n.d. SECONDARY. https://www.assemblyai.com/docs/faq/what-are-the-recommended-options-for-audio-noise-reduction.md
- [S12] A. Islam, R. Nahar, M. E. Hamid, "When Audio Separation Hurts Zero-Shot ASR: Evaluating SAM-Audio with Whisper on Bengali and English Speech", arXiv:2603.04710v2, 2026, Tables I–IV, Sec. IV–V. https://arxiv.org/abs/2603.04710
- [S13] S. Chondhekar et al., "When De-noising Hurts: A Systematic Study of Speech Enhancement Effects on Modern Medical ASR Systems", arXiv:2512.17562, 2025, abstract. https://arxiv.org/abs/2512.17562
- [S14] K. Iwamoto et al., "How Bad Are Artifacts?: Analyzing the Impact of Speech Enhancement Errors on ASR", arXiv:2201.06685 (Interspeech 2022), abstract. https://arxiv.org/abs/2201.06685
- [S15] M. Huo, Y. Zhang, H. Zhang, "Where Speech Enhancement Hurts Recognition: An Inference Time Polar Projection Diagnosis", arXiv:2607.11157, 2026, Sec. I, Table II, Fig. 2. https://arxiv.org/pdf/2607.11157
- [S16] J.-M. Valin, "RNNoise: Learning Noise Suppression" (demo page), 2017-09-27. https://jmvalin.ca/demo/rnnoise/ ; paper: "A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement", MMSP 2018, arXiv:1709.08243.
- [S17] A. Sapeha et al., "A Comparative Study of Noise Effects, VAD, and ASR Methods in Speech Recognition", ICAIIT 2026, DOI 10.25673/123832 (results and conclusion sections). https://icaiit.org/proceedings/14th_ICAIIT_2/3-4-ICAIIT_2026_14(2).pdf
- [S18] S. Braun, H. Gamper, "Effect of noise suppression losses on speech distortion and ASR performance", Microsoft Research, 2021 (abstract). https://www.microsoft.com/en-us/research/publication/effect-of-noise-suppression-losses-on-speech-distortion-and-asr-performance/
- [S19] AudioLab.tools (N. Renting), "Test a noise filter before speech-to-text", test dated 2026-10-15. SECONDARY. https://audiolab.tools/docs/voicelab/test-a-noise-filter-before-stt
- [S20] Gnani AI, "Prisma v3.0" (sections: Languages; Language detection; Output styles; Context; How it differs; What it does not do; Limits), 2026. SECONDARY (vendor). https://docs.gnani.ai/api/STT/models/prisma-v3.md
- [S20a] GitHub issue Rikorose/DeepFilterNet #483, "Deepfilternet degrades Sound Quality for Speech-to-Text Transcription", 2023-12-27. SECONDARY. https://github.com/Rikorose/DeepFilterNet/issues/483
- [S21] Gnani AI, "Realtime streaming" (Connection headers; VAD tuning; Audio format; Client control frames; Prisma v3.0 on streaming), 2026. SECONDARY. https://docs.gnani.ai/api/STT/stt-websocket.md
- [S22] xiph/rnnoise README (48 kHz raw PCM), n.d. https://github.com/xiph/rnnoise
- [S22b] Gnani AI, "Limits", 2026. SECONDARY. https://docs.gnani.ai/api/STT/limits.md
- [S23] Gnani AI Research Team, "How We Benchmark ASR Models: A Technical Deep-Dive into WER, CER, and Indic Dataset Methodology", 2026-05-28. SECONDARY. https://gnani.ai/resources/research/benchmarking-indic-asr-models-a-technical-deep-dive
- [S24] A. Varshinii (Gnani AI), "Prisma v3.0: ASR Model for Indian Languages", 2026-10-28 (table "where wrong transcripts come from"). SECONDARY. https://www.gnani.ai/resources/blogs/prisma-v3-0-speech-recognition
- [S25] Gnani AI, "Available Voices" (Timbre v3.0 voices; Audio tags), 2026. SECONDARY. https://docs.gnani.ai/api/TTS/available-voices.md
- [S26] Gnani AI, "Text-to-Speech (Realtime)" (Models; Connection Flow; Request Parameters; Server Messages), 2026. SECONDARY. https://docs.gnani.ai/api/TTS/tts-websocket.md ; speed and error table also in https://docs.gnani.ai/api/TTS/tts-inference.md
- [S27] Gnani AI, "Pipecat Plugin" (TTS — GnaniTTSService), 2026. SECONDARY. https://docs.gnani.ai/pipecat/introduction.md
- [S27b] Gnani AI, `pipecat-gnani` 0.6.0 wheel, `pipecat_gnani/tts.py` (`GnaniTTSService._connect/_disconnect`, ~L998–1012), PyPI, 2026. https://pypi.org/project/pipecat-gnani/
- [S28] Gnani AI, "Changelog" (Release notes, 22 Oct 2026, Prisma v3.0). SECONDARY. https://docs.gnani.ai/api/introduction/changelog.md
- [S29] Gnani AI, "LiveKit Plugin" (TTS settings), 2026. SECONDARY. https://docs.gnani.ai/livekit/introduction.md
- [S30] Chrome for Developers, "More native echo cancellation" (2018) and "Disabling hardware noise suppression" (Chrome 64), blog. SECONDARY. https://developer.chrome.com/blog/more-native-echo-cancellation/ ; https://developer.chrome.com/blog/disabling-hardware-noise-suppression/
- [S31] Corti, "Audio Configuration" (Dictation; Ambient Conversation; streaming recommendations), n.d. SECONDARY. https://docs.corti.ai/stt/best-practices-audio
- [S32] H. Schröter et al., "DeepFilterNet2: Towards Real-Time Speech Enhancement on Embedded Devices for Full-Band Audio", arXiv:2205.05474 (IWAENC 2022), abstract. https://arxiv.org/abs/2205.05474
- [S33] H. Schröter et al., "DeepFilterNet: Perceptually Motivated Real-Time Speech Enhancement", arXiv:2305.08227 (Interspeech 2023 show & tell), abstract. https://arxiv.org/abs/2305.08227
- [S34] sapphi-red, `@sapphi-red/web-noise-suppressor` README and npm registry (v0.4.1, published 2026-09-19). https://github.com/sapphi-red/web-noise-suppressor
- [S35] S. Maymon et al., "Restoration of Clipped Signals with Application to Speech Recognition", Interspeech 2013 (abstract). https://www.isca-archive.org/interspeech_2013/maymon13b_interspeech.pdf
- [S36] Y. Tachioka et al., "Speech recognition performance estimation for clipped speech based on objective measures", Acoustical Science and Technology 35(6), 2014 (seen via abstract and snippet only). https://www.jstage.jst.go.jp/article/ast/35/6/35_E1415/_pdf/-char/ja
- [S37] CXOToday, "Gnani AI launches Prisma v3.0 …", 2026-10-28. SECONDARY. https://cxotoday.com/media-coverage/gnani-ai-launches-prisma-v3-0-a-speech-to-text-model-trained-on-indian-phone-calls-with-four-transcription-modes/
- [S38] ArtRealmAI (Anabel), "Gnani Prisma v3.0 Transcribes Code-Mixed Indian Calls…", 2026-10-28. SECONDARY. https://artrealmai.com/article/gnani-prisma-v3-indian-code-mixed-speech-to-text
- [S39] Gnani AI, "Audio Tags" (Syntax and Scope; Supported Tags; Billing; Tips), 2026. SECONDARY. https://docs.gnani.ai/api/TTS/tts-audio-tags.md
- [S40] Gnani AI, "Python SDK — Text-to-Speech" (note on per-call WebSocket), 2026. SECONDARY. https://docs.gnani.ai/python-sdk/text-to-speech.md

---

## Risks and open questions

1. **Browser cannot send Gnani headers.** STT and TTS WebSockets need `X-API-Key-ID` and the config as upgrade headers. A backend proxy is required [S21], and it adds one network hop of latency. It also has to re-frame to exactly 1,024-byte, 32 ms frames if the client sends a different size.
2. **Context headers on streaming are contradictory in the docs** [S20][S21] vs [S28][S22b]. Verify `topic` and `speaker_names` actually take effect over the WebSocket, for example with A/B transcripts on a fixed clip.
3. **Vendor NS hidden under `echoCancellation:true`.** On some phones the VOICE_COMMUNICATION preset applies vendor NS that we cannot turn off from JS [S6]. Our "NS off" arm may not really be off. Log `track.getSettings()` and per-device model (`navigator.userAgentData` / UA).
4. **Quiet capture with `echoCancellation:false`** on some Android devices [S3][S8]. Our +12 dB AGC cap may not be enough. Measure RMS per device.
5. **`MODE_IN_COMMUNICATION`** [S2] can route TTS playback to the voice-call stream (earpiece or lower volume) on some devices. UNVERIFIED for Chrome specifically; test on target phones.
6. **No independent Prisma v3.0 noise or code-mix WER data.** All figures are Gnani's [S24][S37][S38]. We need our own 50–100 clip test set (ASHA-style code-mixed Hindi/Kannada, household noise) and should score WER/CER with the same normaliser for every arm.
7. **WASM denoiser CPU on low-end phones is unmeasured.** RNNoise is 48 kHz-native [S22], so it adds resampling cost. Worklet underruns would also break Gnani's real-time cadence requirement [S21].
8. **TTS barge-in requires a reconnect** [S26][S27b]. Measure reconnect and first-chunk latency, or keep a warm spare socket. Billing for partially streamed text after close is UNVERIFIED.
9. **`<pauses>` length is fixed and undocumented** [S39]. Repeating the tag for longer pauses, and `hi-en` language with v3.0, are UNVERIFIED.
10. **Chromium behaviour can change.** Findings come from `main` on 2026-11-13. The Android Chrome version on ASHA phones may be older; the OpenSL ES vs AAudio path depends on the `kUseAAudioInput` feature state [S2].
