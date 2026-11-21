"""Replay the same synthetic phone WAV against different Prisma settings."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import wave

from dotenv import load_dotenv
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus, WebSocketException

from asha.gnani import COMMIT_MESSAGE, FRAME_BYTES, Reframer, stt_headers, visit_keyterms
from smoke_gnani import PRISMA, ROOT, RATE, FRAME_SECONDS


class PrismaRelay:
    """Replace expired upstream sockets without restarting the phone visit."""

    def __init__(self, headers):
        self.headers = headers
        self.socket = None
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        await self.connection()
        return self

    async def __aexit__(self, *_):
        if self.socket:
            await self.socket.close()

    async def connection(self):
        async with self.lock:
            if self.socket is None:
                for attempt in range(3):
                    try:
                        socket = await connect(PRISMA, additional_headers=self.headers,
                                               open_timeout=5, close_timeout=0.25)
                        break
                    except (OSError, TimeoutError):
                        if attempt == 2:
                            raise
                        await asyncio.sleep(0.25 * (attempt + 1))
                try:
                    ready = json.loads(await asyncio.wait_for(socket.recv(), 5))
                    if ready.get("type") != "connected":
                        raise RuntimeError("Prisma rejected session setup")
                except BaseException:
                    await socket.close()
                    raise
                self.socket = socket
            return self.socket

    async def invalidate(self, socket):
        async with self.lock:
            if self.socket is socket:
                self.socket = None
                await socket.close()

    async def send(self, data):
        socket = await self.connection()
        try:
            await socket.send(data)
        except ConnectionClosed:
            await self.invalidate(socket)
            socket = await self.connection()
            await socket.send(data)

    async def __aiter__(self):
        while True:
            socket = await self.connection()
            try:
                message = await socket.recv()
            except ConnectionClosed:
                await self.invalidate(socket)
                continue
            event = json.loads(message)
            if event.get("type") == "error":
                reason = str(event.get("message", "")).lower()
                if any(word in reason for word in ("idle", "maximum session", "session limit")):
                    await self.invalidate(socket)
                    continue
            yield event


async def upload(socket, pcm):
    frames = Reframer()
    for frame in frames.push(pcm):
        await socket.send(frame)
        await asyncio.sleep(FRAME_SECONDS)
    if tail := frames.flush():
        await socket.send(tail)
        await asyncio.sleep(FRAME_SECONDS)
    await socket.send(COMMIT_MESSAGE)


async def transcribe(headers, pcm):
    async with connect(PRISMA, additional_headers=headers, open_timeout=8) as socket:
        ready = json.loads(await asyncio.wait_for(socket.recv(), 8))
        if ready.get("type") != "connected":
            print(f"  Setup rejected ({ready.get('type', 'unknown event')})")
            return False
        print("  Connected:", ready.get("config", {}).get("language_code", "locale not echoed"))
        sender = asyncio.create_task(upload(socket, pcm))
        count = 0
        try:
            while True:
                try:
                    timeout = 2 if sender.done() and count else 12
                    event = json.loads(await asyncio.wait_for(socket.recv(), timeout))
                except TimeoutError:
                    await sender
                    if not count:
                        print("  No transcript")
                    return bool(count)
                if event.get("type") == "error":
                    print("  Prisma returned a streaming error")
                    return False
                if event.get("type") == "transcript" and event.get("text"):
                    count += 1
                    print(f"  [{event.get('detected_language_code', '?')}] {event['text']}")
        finally:
            if not sender.done():
                sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)


async def compare(args, key, pcm):
    terms = visit_keyterms(args.visit, args.language)
    locale = [f"{args.language}-IN"]
    cases = [
        ("Baseline", locale, {}),
        (f"Visit hints ({len(terms)} terms)", locale, {"keyterms": terms}),
    ]
    if args.probe_context:
        cases.extend([
            ("Automatic language + visit hints", ["indic-auto"], {"keyterms": terms}),
            ("Topic and speaker name probe", locale, {
                "keyterms": terms, "topic": "Synthetic ASHA home visit", "speaker_names": ["Sunita"],
            }),
        ])

    results = []
    for name, languages, context in cases:
        print(name, flush=True)
        try:
            results.append(await transcribe(stt_headers(key, languages, **context), pcm))
        except InvalidStatus as exc:
            print(f"  Handshake rejected (HTTP {exc.response.status_code})")
            results.append(False)
        except ConnectionClosed as exc:
            close = exc.rcvd or exc.sent
            print(f"  Connection ended (code {close.code if close else 1006})")
            results.append(False)
        except (WebSocketException, OSError, TimeoutError):
            print("  Could not complete the connection")
            results.append(False)
    return 0 if all(results[:2]) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", help="Synthetic 16 kHz mono PCM WAV, such as the phone debug download")
    parser.add_argument("--visit", choices=("anc", "pnc", "hbnc", "hbyc"), default="anc")
    parser.add_argument("--language", choices=("hi", "kn", "en"), default="hi")
    parser.add_argument("--probe-context", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key:
        parser.error("Set GNANI_API_KEY in the repository's .env")
    try:
        with wave.open(args.wav, "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, RATE):
                parser.error("Expected a 16 kHz, 16-bit mono PCM WAV")
            pcm = audio.readframes(audio.getnframes())
    except (OSError, EOFError, wave.Error) as exc:
        parser.error(str(exc))
    if not pcm:
        parser.error("The WAV is empty")
    return asyncio.run(compare(args, key, pcm))


if __name__ == "__main__":
    sys.exit(main())
