import json

import pytest

from asha.gnani import (FRAME_BYTES, ConfigError, Reframer, select_keyterms, split_finish_cue, stt_headers,
                        tts_request, update_keyterms_message)
from asha.numbers import unit_words


def test_headers_always_send_format_and_escape_keyterms():
    h = stt_headers("k", ["kn-IN", "hi-IN", "en-IN"], ["ಮಡಿಲು", "ANC"], x_min_silence_ms=800)
    assert h["format"] == "codemix" and h["model"] == "prisma-v3.0"
    assert "\\u" in h["keyterms"] and h["keyterms"].isascii()
    assert json.loads(h["keyterms"]) == ["ಮಡಿಲು", "ANC"]
    assert h["x-min-silence-ms"] == "800"


@pytest.mark.parametrize("kwargs", [
    dict(languages=["hi-IN"] * 5), dict(languages=["xx-IN"]), dict(languages=["hi-IN"], keyterms=["a"] * 201),
    dict(languages=["hi-IN"], topic="x" * 1601), dict(languages=["hi-IN"], keyterms=["<|bad|>"]),
    dict(languages=["hi-IN"], x_vad_threshold=1.5), dict(languages=["hi-IN"], sample_rate=22050),
])
def test_invalid_settings_raise(kwargs):
    with pytest.raises(ConfigError):
        stt_headers("k", **kwargs)


def test_keyterms_fit_and_contain_no_number_words():
    k = select_keyterms()
    assert 150 <= len(k) <= 200 and len(set(k)) == len(k)
    assert not set(t.lower() for t in k) & set(unit_words())
    assert "ANC" in k


def test_update_settings_message():
    assert json.loads(update_keyterms_message(["IFA"])) == {"type": "update_settings", "bias": {"list": ["IFA"]}}


def test_reframer_emits_exact_frames():
    r = Reframer()
    frames = r.push(b"\x01" * 1500) + r.push(b"\x02" * 600)
    assert [len(f) for f in frames] == [FRAME_BYTES, FRAME_BYTES]
    tail = r.flush()
    assert len(tail) == FRAME_BYTES and r.flush() is None


def test_tts_request():
    req = tts_request("नमस्ते", "hi", voice="Chetana")
    assert req["audio_config"]["container"] == "raw" and req["model"] == "timbre-v3.0"
    for bad in [dict(speed=1.3), dict(voice="Nalini"), dict(language="auto")]:
        with pytest.raises(ConfigError):
            tts_request("x", **{"language": "hi", **bad})
    with pytest.raises(ConfigError):
        tts_request("agla visit 23/06", "hi")


@pytest.mark.parametrize(("transcript", "note", "finished"), [
    ("I’m done!", "", True),
    ("Weight 52 kg, I am done.", "Weight 52 kg", True),
    ("katham.", "", True),
    ("ख़त्म।", "", True),
    ("52 kilo. Khatam.", "52 kilo", True),
    ("ರಕ್ತಸ್ರಾವ ಇಲ್ಲ, ಮಾತು ಮುಗಿಯಿತು.", "ರಕ್ತಸ್ರಾವ ಇಲ್ಲ", True),
    ("maatu mugiyitu", "", True),
    ("bleeding khatam", "bleeding khatam", False),
    ("ಆ ನೋವು ಮುಗಿಯಿತು", "ಆ ನೋವು ಮುಗಿಯಿತು", False),
    ("I am done taking the tablets", "I am done taking the tablets", False),
])
def test_hands_free_finish_cue(transcript, note, finished):
    assert split_finish_cue(transcript) == (note, finished)
