"""Gnani Prisma v3.0 / Timbre v3.0 settings, validated against research/03-audio-gnani.md.

No network code here: these build the upgrade headers and request messages the
backend relay sends (a browser WebSocket cannot set headers, so the relay is
mandatory and also keeps the API key off the phone).
"""
from __future__ import annotations

import csv
import json
import re

from .numbers import unit_words
from .text import DATA

SUPPORTED_LANGS = {"bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"}
FORMATS = {"verbatim", "transcribe", "codemix", "transliterate"}
VAD_RANGES = {  # header: (min, max, default)
    "x-vad-threshold": (0.0, 1.0, 0.7),
    "x-min-silence-ms": (100, 2000, 500),
    "x-min-speech-ms": (50, 2000, 100),
    "x-min-segment-ms": (100, 1000, 120),
    "x-max-speech-s": (5, 120, None),
    "x-idle-timeout-sec": (5, 900, 60),
}
FRAME_BYTES = 1024          # 512 samples of 16-bit mono at 16 kHz = 32 ms
TIMBRE_VOICES = {"Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika",
                 "Avinash", "Shubham", "Prakash", "Devansh", "Yashraj", "Harshad"}
TTS_SAMPLE_RATES = {8000, 16000, 22050, 24000, 44100, 48000}


class ConfigError(ValueError):
    pass


def _no_markers(value: str) -> str:
    if "<|" in value or "|>" in value:
        raise ConfigError("context values may not contain '<|' or '|>'")
    return value


def stt_headers(api_key_id: str, languages: list[str], keyterms: list[str] = (),
                topic: str | None = None, speaker_names: list[str] = (),
                fmt: str = "codemix", sample_rate: int = 16000, **vad) -> dict[str, str]:
    """Headers for wss://api.vachana.ai/stt/v3/stream.

    `format` is always sent explicitly: the default changes with language_code
    (single hi-IN gives digits, kn-IN gives native number words).
    VAD keys use underscores: x_min_silence_ms=800.
    """
    if not 1 <= len(languages) <= 4:
        raise ConfigError("Prisma accepts 1-4 language hints")
    for l in languages:
        if l != "indic-auto" and l.split("-")[0] not in SUPPORTED_LANGS:
            raise ConfigError(f"unsupported language {l}")
    if fmt not in FORMATS:
        raise ConfigError(f"format must be one of {sorted(FORMATS)}")
    if sample_rate not in {8000, 16000, 44100, 48000}:
        raise ConfigError("x-sample-rate must be 8000, 16000, 44100 or 48000")
    headers = {
        "x-api-key-id": api_key_id, "model": "prisma-v3.0",
        "language_code": ",".join(languages), "format": fmt, "x-sample-rate": str(sample_rate),
    }
    if keyterms:
        if len(keyterms) > 200:
            raise ConfigError("at most 200 keyterms (the streaming API silently ignores invalid values)")
        # non-ASCII must be \\uXXXX-escaped inside a header
        headers["keyterms"] = json.dumps([_no_markers(k) for k in keyterms], ensure_ascii=True)
    if topic:
        if len(topic) > 1600:
            raise ConfigError("topic is at most 1,600 characters")
        headers["topic"] = json.dumps(_no_markers(topic), ensure_ascii=True)[1:-1]
    if speaker_names:
        if not 1 <= len(speaker_names) <= 4:
            raise ConfigError("speaker_names takes 1-4 names (a spelling hint, not diarization)")
        headers["speaker_names"] = json.dumps([_no_markers(n) for n in speaker_names], ensure_ascii=True)
    for key, value in vad.items():
        header = "x-" + key.removeprefix("x_").replace("_", "-")
        if header not in VAD_RANGES:
            raise ConfigError(f"unknown VAD setting {key}")
        lo, hi, _ = VAD_RANGES[header]
        if not lo <= value <= hi:
            raise ConfigError(f"{header} must be within {lo}-{hi}")
        headers[header] = str(value)
    return headers


def update_keyterms_message(keyterms: list[str]) -> str:
    """Mid-session keyterm swap; applies from the next utterance."""
    if len(keyterms) > 200:
        raise ConfigError("at most 200 keyterms")
    return json.dumps({"type": "update_settings", "bias": {"list": keyterms}}, ensure_ascii=False)


COMMIT_MESSAGE = json.dumps({"type": "commit"})


# ───────────────────────── keyterms from the glossary ─────────────────────────

_KANNADA = re.compile(r"[ಀ-೿]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _script_forms(cell: str, pattern: re.Pattern) -> list[str]:
    out = []
    for alt in cell.split(";"):
        script = alt.split("(")[0].strip()
        if script and pattern.search(script):
            out.append(script)
    return out


def select_keyterms(latin: int = 100, kannada: int = 60, devanagari: int = 40) -> list[str]:
    """200 slots from data/glossary.csv: Latin canonical terms, then native-script local words.

    No number words: they waste slots and numbers are handled by the normaliser.
    """
    numbers = set(unit_words())
    rows = list(csv.DictReader(open(DATA / "glossary.csv", encoding="utf-8")))
    picked: list[str] = []
    seen: set[str] = set()

    def add(term: str, bucket: list[str], cap: int) -> None:
        t = term.strip()
        if t and t.lower() not in seen and t.lower() not in numbers and len(bucket) < cap:
            seen.add(t.lower())
            bucket.append(t)

    lat, kn, dev = [], [], []
    for r in rows:
        canonical = r["canonical"]
        add(canonical.split("(")[0], lat, latin)
        for inner in re.findall(r"\(([A-Za-z0-9 .-]{2,12})\)", canonical):
            add(inner, lat, latin)               # "Anganwadi worker (AWW)" -> AWW
    for r in rows:
        for t in _script_forms(r["kn_spoken"], _KANNADA)[:1]:
            add(t, kn, kannada)
        for t in _script_forms(r["hi_spoken"], _DEVANAGARI)[:1]:
            add(t, dev, devanagari)
    picked = lat + kn + dev
    return picked[:200]


# ───────────────────────── audio framing ─────────────────────────

class Reframer:
    """Re-cuts arbitrary PCM chunks into exact 1,024-byte frames for Prisma.

    The browser should already send exact frames; this guards the relay.
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def push(self, chunk: bytes) -> list[bytes]:
        self._buf += chunk
        frames = []
        while len(self._buf) >= FRAME_BYTES:
            frames.append(bytes(self._buf[:FRAME_BYTES]))
            del self._buf[:FRAME_BYTES]
        return frames

    def flush(self) -> bytes | None:
        """Pad the tail with silence at the end of an utterance (before `commit`)."""
        if not self._buf:
            return None
        frame = bytes(self._buf) + b"\x00" * (FRAME_BYTES - len(self._buf))
        self._buf.clear()
        return frame


# ───────────────────────── TTS ─────────────────────────

def tts_request(text: str, language: str, voice: str = "Chetana", speed: float = 1.0,
                sample_rate: int = 24000) -> dict:
    """One Timbre v3.0 request. Raw PCM so it can stream (ogg arrives as one chunk).

    There is no cancel message: to stop speech on barge-in, close the socket,
    drop queued audio and reconnect (keep a warm spare socket).
    """
    if voice not in TIMBRE_VOICES:
        raise ConfigError(f"{voice} is not a Timbre v3.0 voice")
    if not 0.85 <= speed <= 1.15:
        raise ConfigError("speed must be within 0.85-1.15")
    if language.split("-")[0] not in SUPPORTED_LANGS:
        raise ConfigError("set an explicit TTS language; never rely on auto for numbers")
    if sample_rate not in TTS_SAMPLE_RATES:
        raise ConfigError("unsupported TTS sample rate")
    if re.search(r"\b\d{1,2}/\d{1,2}\b(?!/)", text):
        raise ConfigError("bare dd/mm is read as a fraction: verbalise dates first")
    return {"text": text, "model": "timbre-v3.0", "voice": voice, "language": language.split("-")[0],
            "speed": speed, "audio_config": {"container": "raw", "encoding": "pcm_s16le",
                                             "sample_rate": sample_rate}}
