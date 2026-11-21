"""Stream guarded speech from Timbre, with a warm socket per visit."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from collections import deque

from anyio import BrokenResourceError, ClosedResourceError
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from asha.gnani import tts_request
from asha.speak import Speaker

TIMBRE = "wss://api.vachana.ai/api/v1/tts"
LOG = logging.getLogger(__name__)
PHONE_CLOSED = (BrokenResourceError, ClosedResourceError, WebSocketDisconnect)


async def open_timbre(key):
    return await connect(TIMBRE, additional_headers={"X-API-Key-ID": key},
                         open_timeout=5, close_timeout=0.25)


async def synthesize(socket, text, lang, voice):
    await socket.send(json.dumps(tts_request(text, lang, voice=voice)))
    async with asyncio.timeout(30):
        while True:
            event = json.loads(await socket.recv())
            kind = event.get("type")
            if kind == "error":
                raise RuntimeError("Timbre rejected synthesis")
            if kind in {"audio", "complete"}:
                data = event["data"].get("audio")
                if data:
                    yield base64.b64decode(data, validate=True)
            if kind == "complete":
                return


class Timbre:
    def __init__(self, key):
        self.key = key
        self.voice = os.getenv("GNANI_TTS_VOICE", "Chetana")
        self.cache = {}

    async def prewarm(self):
        for lang in ("hi", "kn", "en"):
            speaker = Speaker(lang)
            for phrase in ("disclosure", "saved"):
                text = speaker.say(phrase)
                try:
                    socket = await open_timbre(self.key)
                    try:
                        pcm = b"".join([chunk async for chunk in synthesize(socket, text, lang, self.voice)])
                        if pcm:
                            self.cache[lang, text] = pcm
                    finally:
                        await socket.close()
                except (WebSocketException, OSError, RuntimeError, TimeoutError, ValueError, KeyError):
                    LOG.warning("Timbre cache warmup failed for %s/%s", lang, phrase)


class VisitSpeech:
    def __init__(self, timbre, phone, lang):
        self.timbre = timbre
        self.phone = phone
        self.lang = lang
        self.lines = deque()
        self.worker = None
        self.closing = False
        self.spare = asyncio.create_task(open_timbre(timbre.key))

    def queue(self, lines):
        self.lines.extend(line for line in lines if line)
        if self.lines and (self.worker is None or self.worker.done()):
            self.worker = asyncio.create_task(self.stream())

    async def stream(self):
        try:
            await self.phone.send_json({"type": "speaking", "on": True})
            while self.lines:
                text = self.lines.popleft()
                cached = self.timbre.cache.get((self.lang, text))
                if cached:
                    for offset in range(0, len(cached), 3840):
                        await self.phone.send_bytes(cached[offset:offset + 3840])
                    continue
                # Shield the idle socket so interruption only closes the active one.
                spare = self.spare
                try:
                    socket = await asyncio.shield(spare)
                except (WebSocketException, OSError, TimeoutError):
                    self.spare = asyncio.create_task(open_timbre(self.timbre.key))
                    raise
                self.spare = asyncio.create_task(open_timbre(self.timbre.key))
                try:
                    async for chunk in synthesize(socket, text, self.lang, self.timbre.voice):
                        await self.phone.send_bytes(chunk)
                finally:
                    await socket.close()
        except PHONE_CLOSED:
            self.lines.clear()
        except (WebSocketException, OSError, RuntimeError, TimeoutError, ValueError, KeyError):
            self.lines.clear()
            LOG.warning("Timbre speech stream ended early")
        finally:
            if not self.closing:
                try:
                    await self.phone.send_json({"type": "speaking", "on": False})
                except PHONE_CLOSED + (OSError, RuntimeError):
                    pass

    async def interrupt(self):
        self.lines.clear()
        if self.worker:
            if not self.worker.done():
                self.worker.cancel()
            await asyncio.gather(self.worker, return_exceptions=True)

    async def close(self):
        self.closing = True
        await self.interrupt()
        self.spare.cancel()
        (socket,) = await asyncio.gather(self.spare, return_exceptions=True)
        if not isinstance(socket, BaseException):
            await socket.close()
