"""Stream guarded speech from Timbre, with a warm socket per visit."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from collections import deque
from contextlib import aclosing

from anyio import BrokenResourceError, ClosedResourceError
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.protocol import State

from asha.gnani import tts_request
from asha.speak import Speaker, TEMPLATES

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
        self.acknowledgements = {}

    async def prewarm(self):
        for lang in ("hi", "kn", "en"):
            speaker = Speaker(lang)
            for phrase in ("disclosure", "saved", "confirm_short", "acknowledge"):
                if lang not in TEMPLATES.get(phrase, {}):
                    continue
                text = speaker.say(phrase)
                try:
                    socket = await open_timbre(self.key)
                    try:
                        pcm = b"".join([chunk async for chunk in synthesize(socket, text, lang, self.voice)])
                        if pcm:
                            self.cache[lang, text] = pcm
                            if phrase == "acknowledge":
                                self.acknowledgements[lang] = text
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

    @property
    def busy(self):
        return self.worker is not None and not self.worker.done()

    def cached_acknowledgement(self):
        return self.timbre.acknowledgements.get(self.lang)

    def queue(self, lines, on_first=lambda: None):
        for line in filter(None, lines):
            if (self.lang, line) in self.timbre.cache:
                self.lines.append((line, on_first))
            else:
                for sentence in re.split(r"(?<=[.!?।])\s+", line.strip()):
                    self.lines.append((sentence, on_first))
        if self.lines and not self.busy:
            self.worker = asyncio.create_task(self.stream())

    async def stream(self):
        try:
            await self.phone.send_json({"type": "speaking", "on": True})
            while self.lines:
                text, on_first = self.lines.popleft()
                cached = self.timbre.cache.get((self.lang, text))
                if cached:
                    on_first()
                    for offset in range(0, len(cached), 3840):
                        await self.phone.send_bytes(cached[offset:offset + 3840])
                    continue
                async with aclosing(self.stream_sentence(text, on_first)) as audio:
                    async for chunk in audio:
                        await self.phone.send_bytes(chunk)
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

    async def stream_sentence(self, text, on_first):
        # The spare may have expired while the worker was dictating. Retry once
        # before any PCM is sent, so a retry cannot repeat audible words.
        for attempt in range(2):
            try:
                socket = await asyncio.shield(self.spare)
            except (WebSocketException, OSError, TimeoutError):
                self.spare = asyncio.create_task(open_timbre(self.timbre.key))
                if attempt:
                    raise
                continue
            self.spare = asyncio.create_task(open_timbre(self.timbre.key))
            first = True
            try:
                if socket.state is not State.OPEN:
                    if attempt:
                        raise RuntimeError("Timbre spare expired")
                    continue
                async for chunk in synthesize(socket, text, self.lang, self.timbre.voice):
                    if first:
                        on_first()
                        first = False
                    yield chunk
                return
            except ConnectionClosed:
                if attempt or not first:
                    raise
            finally:
                await socket.close()

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
