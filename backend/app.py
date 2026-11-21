"""Serve the phone page and relay one visit's audio to Prisma."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from websockets.exceptions import WebSocketException

from asha.gnani import COMMIT_MESSAGE, FRAME_BYTES, stt_headers, visit_keyterms
from asha.visit import Visit
from stt import PrismaRelay
from tts import Timbre, VisitSpeech

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
FRAME_SECONDS = FRAME_BYTES / (16000 * 2)
LANGUAGES = {"hi", "kn", "en"}
VISIT_TYPES = {"anc", "pnc", "hbnc", "hbyc"}
DEMO_BENEFICIARIES = [
    {"id": "demo-anc", "name": "Sunita Devi", "visit_type": "anc"},
    {"id": "demo-hbnc", "name": "Baby of Kavya", "visit_type": "hbnc"},
]

load_dotenv(ROOT / ".env")
@asynccontextmanager
async def lifespan(app):
    key = os.getenv("GNANI_API_KEY", "").strip()
    app.state.timbre = Timbre(key)
    warmup = asyncio.create_task(app.state.timbre.prewarm()) if key else None
    try:
        yield
    finally:
        if warmup:
            warmup.cancel()
            await asyncio.gather(warmup, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


class VisitTurn:
    def __init__(self, phone, visit, speech, hands_free):
        self.phone = phone
        self.hands_free = hands_free
        self.visit = visit
        self.speech = speech
        self.holding = False
        self.pending_speech = []
        self.has_transcript = False
        self.committed = False
        self.readback_done = False
        self.timer = None

    async def emit(self, lines):
        events = getattr(self.visit, "events", lambda: [])
        for event in events():
            await self.phone.send_json(event)
        if self.holding:
            self.pending_speech.extend(lines)
        else:
            self.speech.queue(lines)

    def schedule_readback(self, delay):
        if self.readback_done:
            return
        if self.timer:
            self.timer.cancel()
        if self.committed and self.has_transcript and not self.holding:
            self.timer = asyncio.create_task(self.readback(delay))

    async def readback(self, delay):
        # Prisma has no commit-complete event in the browser contract. Allow
        # recently finalized VAD segments to arrive before the first readback.
        await asyncio.sleep(delay)
        self.readback_done = True
        await self.emit(self.visit.readback())

    async def close(self):
        if self.timer:
            self.timer.cancel()
            await asyncio.gather(self.timer, return_exceptions=True)
        await self.speech.close()


@app.get("/api/beneficiaries")
def beneficiaries():
    data = BACKEND / "data" / "beneficiaries.json"
    if data.is_file():
        return FileResponse(data, media_type="application/json")
    return DEMO_BENEFICIARIES


async def send_audio(phone: WebSocket, prisma, turn: VisitTurn) -> None:
    loop = asyncio.get_running_loop()
    next_frame = loop.time()
    while True:
        message = await phone.receive()
        if message["type"] == "websocket.disconnect":
            return
        frame = message.get("bytes")
        if frame is not None:
            if not turn.hands_free and not turn.holding:
                turn.holding = True
                turn.schedule_readback(0)
            if len(frame) != FRAME_BYTES:
                await phone.close(code=1008, reason="Expected 1024-byte PCM frames")
                return
            await asyncio.sleep(max(0, next_frame - loop.time()))
            next_frame = max(next_frame + FRAME_SECONDS, loop.time())
            await prisma.send(frame)
        elif message.get("text"):
            event = json.loads(message["text"])
            if isinstance(event, dict) and event.get("type") == "commit":
                await asyncio.sleep(max(0, next_frame - loop.time()))
                await prisma.send(COMMIT_MESSAGE)
                turn.holding = False
                turn.speech.queue(turn.pending_speech)
                turn.pending_speech.clear()
                turn.committed = True
                turn.schedule_readback(0.9)
            elif isinstance(event, dict) and event.get("type") == "barge_in":
                await turn.speech.interrupt()


async def send_transcripts(phone: WebSocket, prisma, locale: str, turn: VisitTurn) -> None:
    async for event in prisma:
        if event.get("type") == "error":
            raise RuntimeError("Prisma reported an error")
        if event.get("type") == "transcript" and event.get("text", "").strip():
            await phone.send_json({
                "type": "transcript",
                "text": event["text"],
                "lang": event.get("detected_language_code") or locale,
            })
            latency = event.get("latency")
            if isinstance(latency, (int, float)):
                await phone.send_json({"type": "latency", "ms": latency})
            turn.has_transcript = True
            if turn.hands_free:
                turn.committed = True
            await turn.emit(turn.visit.hear(event["text"], event.get("detected_language_code") or locale))
            turn.schedule_readback(0.35)


@app.websocket("/ws")
async def visit_socket(phone: WebSocket) -> None:
    await phone.accept()
    try:
        start = await asyncio.wait_for(phone.receive_json(), timeout=15)
        if (not isinstance(start, dict) or start.get("type") != "start_visit"
                or start.get("lang") not in LANGUAGES or start.get("visit_type") not in VISIT_TYPES
                or not isinstance(start.get("beneficiary_id"), str) or not start["beneficiary_id"]):
            await phone.close(code=1008, reason="Expected a valid start_visit")
            return
        key = os.getenv("GNANI_API_KEY", "").strip()
        if not key:
            await phone.close(code=1011, reason="GNANI_API_KEY is missing on the server")
            return
        locale = f"{start['lang']}-IN"
        subject = {"hbnc": "newborn", "hbyc": "child"}.get(start["visit_type"], "mother")
        visit = Visit(start["visit_type"], subject, start["lang"],
                      beneficiary_id=start["beneficiary_id"])
        terms = visit_keyterms(start["visit_type"], start["lang"])
        headers = stt_headers(key, [locale], keyterms=terms)
        async with PrismaRelay(headers) as prisma:
            timbre = phone.app.state.timbre
            turn = VisitTurn(phone, visit, VisitSpeech(timbre, phone, start["lang"]),
                             hands_free=phone.query_params.get("hands_free") == "1")
            await turn.emit(visit.start())
            upload = asyncio.create_task(send_audio(phone, prisma, turn))
            download = asyncio.create_task(send_transcripts(phone, prisma, locale, turn))
            try:
                done, _ = await asyncio.wait((upload, download), return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
                if download in done and upload not in done:
                    await phone.close(code=1011, reason="Prisma connection ended")
            finally:
                for task in (upload, download):
                    task.cancel()
                await asyncio.gather(upload, download, return_exceptions=True)
                await turn.close()
    except WebSocketDisconnect:
        pass
    except (json.JSONDecodeError, KeyError, TypeError):
        with suppress(RuntimeError, WebSocketDisconnect):
            await phone.close(code=1008, reason="Invalid WebSocket message")
    except (WebSocketException, OSError, RuntimeError, TimeoutError):
        with suppress(RuntimeError, WebSocketDisconnect):
            await phone.close(code=1011, reason="Speech connection failed. Try again.")


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
