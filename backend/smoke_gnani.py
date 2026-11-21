"""Run the Timbre-to-Prisma WebSocket smoke test from the repository root."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import wave
from pathlib import Path

from dotenv import load_dotenv
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from asha.gnani import COMMIT_MESSAGE, FRAME_BYTES, Reframer, stt_headers, tts_request
from asha.speak import Speaker

ROOT = Path(__file__).resolve().parents[1]
CLIP = ROOT / "eval" / "clips" / "hello.wav"
TIMBRE = "wss://api.vachana.ai/api/v1/tts"
PRISMA = "wss://api.vachana.ai/stt/v3/stream"
RATE = 16000
SAMPLE_BYTES = 2
FRAME_SECONDS = FRAME_BYTES / (RATE * SAMPLE_BYTES)
RESPONSE_TIMEOUT = 20


class SmokeError(Exception):
    pass


async def receive(socket, service: str, key: str, timeout: float) -> dict:
    message = await asyncio.wait_for(socket.recv(), timeout)
    if not isinstance(message, str):
        raise SmokeError(f"{service} returned binary data where JSON was expected")
    event = json.loads(message)
    if not isinstance(event, dict):
        raise SmokeError(f"{service} returned a JSON value instead of an object")
    logged = event
    if service == "Timbre" and event.get("type") == "audio":
        data = event["data"]
        logged = {**event, "data": {**data, "audio": f"<{len(data['audio'])} base64 characters>"}}
    print(f"{service} < {json.dumps(logged, ensure_ascii=False).replace(key, '[redacted]')}",
          flush=True)
    if event.get("type") == "error":
        raise SmokeError(f"{service} returned an error (see the event above)")
    return event


async def synthesize(key: str) -> None:
    disclosure = Speaker("hi").say("disclosure")
    request = tts_request(disclosure, "hi", sample_rate=RATE)
    pcm = bytearray()
    async with connect(TIMBRE, additional_headers={"X-API-Key-ID": key}) as socket:
        await socket.send(json.dumps(request))
        while True:
            event = await receive(socket, "Timbre", key, RESPONSE_TIMEOUT)
            if event.get("type") == "audio":
                pcm.extend(base64.b64decode(event["data"]["audio"], validate=True))
            if event.get("type") == "complete":
                break

    if not pcm or len(pcm) % SAMPLE_BYTES:
        raise SmokeError("Timbre did not return complete 16-bit PCM samples")
    CLIP.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(CLIP), "wb") as wav:
        wav.setparams((1, SAMPLE_BYTES, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(pcm)
    print(f"Wrote {CLIP.relative_to(ROOT)}", flush=True)


async def replay(socket) -> None:
    reframer = Reframer()
    with wave.open(str(CLIP), "rb") as wav:
        while chunk := wav.readframes(FRAME_BYTES // SAMPLE_BYTES):
            for frame in reframer.push(chunk):
                await socket.send(frame)
                await asyncio.sleep(FRAME_SECONDS)
        if tail := reframer.flush():
            await socket.send(tail)
            await asyncio.sleep(FRAME_SECONDS)
    await socket.send(COMMIT_MESSAGE)


async def transcribe(key: str) -> None:
    # The live endpoint requires one locale for this smoke test.
    headers = stt_headers(key, ["hi-IN"])
    async with connect(PRISMA, additional_headers=headers) as socket:
        sender = asyncio.create_task(replay(socket))
        got_transcript = False
        try:
            while True:
                # VAD can emit transcripts during replay. After commit, drain queued
                # messages and give Prisma time to return the last segment.
                timeout = 2 if sender.done() and got_transcript else RESPONSE_TIMEOUT
                try:
                    event = await receive(socket, "Prisma", key, timeout)
                except TimeoutError:
                    await sender
                    if got_transcript:
                        return
                    raise SmokeError("Prisma returned no nonempty transcript after commit") from None
                if event.get("type") == "transcript" and str(event.get("text") or "").strip():
                    got_transcript = True
        finally:
            if not sender.done():
                sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)


async def run(key: str) -> int:
    for service, operation in (("Timbre", synthesize), ("Prisma", transcribe)):
        try:
            await operation(key)
        except InvalidStatus as exc:
            message = f"WebSocket handshake rejected (HTTP {exc.response.status_code})"
        except ConnectionClosed as exc:
            close = exc.rcvd or exc.sent
            message = f"WebSocket closed (code {close.code if close else 1006})"
        except TimeoutError:
            message = "Timed out waiting for the WebSocket"
        except (OSError, ValueError, KeyError, TypeError, SmokeError) as exc:
            message = str(exc).replace(key, "[redacted]")
        else:
            continue
        print(f"{service}: {message}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key:
        print("Set GNANI_API_KEY in the repository's .env file.", file=sys.stderr)
        return 1
    return asyncio.run(run(key))


if __name__ == "__main__":
    raise SystemExit(main())
