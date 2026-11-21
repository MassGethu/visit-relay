"""Serve the phone page and relay one visit's audio to Prisma."""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from websockets.exceptions import WebSocketException

from asha.gnani import COMMIT_MESSAGE, FRAME_BYTES, stt_headers, visit_keyterms
from asha.visit import Visit
from llm import understand
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

LOG = logging.getLogger(__name__)
TIMING_FILE = ROOT / "eval" / "latency.csv"
TIMING_LOCK = Lock()

load_dotenv(ROOT / ".env")


def write_timing(session, turn, stage, timestamp_ms):
    try:
        with TIMING_LOCK:
            TIMING_FILE.parent.mkdir(parents=True, exist_ok=True)
            with TIMING_FILE.open("a+", newline="", encoding="utf-8") as stream:
                stream.seek(0, os.SEEK_END)
                writer = csv.writer(stream)
                if not stream.tell():
                    writer.writerow(("session", "turn", "stage", "timestamp_ms"))
                writer.writerow((session, turn, stage, f"{timestamp_ms:.3f}"))
    except OSError:
        LOG.warning("Could not write voice timing CSV")


class BrowserTiming(BaseModel):
    session: UUID
    turn: int = Field(gt=0, le=10000)
    stage: Literal["release", "first_audio_played"]
    timestamp_ms: float = Field(gt=0, le=1e13)


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
    def __init__(self, phone, visit, speech, hands_free, session_id, llm_turns):
        self.phone = phone
        self.session_id = session_id
        self.llm_turns = llm_turns
        self.visit_lock = asyncio.Lock()
        self.turn_number = 0
        self.reply_turn = 0
        self.seen_timings = set()
        self.open_utterances = set()
        self.hands_free = hands_free
        self.visit = visit
        self.speech = speech
        self.holding = False
        self.pending_speech = []
        self.has_transcript = False
        self.committed = False
        self.readback_done = False
        self.timer = None

    def mark(self, number, stage):
        point = (number, stage)
        if number and point not in self.seen_timings:
            self.seen_timings.add(point)
            write_timing(self.session_id, number, stage, time.time_ns() / 1e6)

    def queue(self, lines, number):
        self.speech.queue(lines, on_first=lambda: self.mark(number, "first_tts_byte"))

    async def emit(self, lines, events, number=0):
        for event in events:
            await self.phone.send_json(event)
        if self.holding:
            self.pending_speech.extend(lines)
        else:
            self.queue(lines, number)

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
        number = self.reply_turn
        async with self.visit_lock:
            await self.emit(self.visit.readback(), self.visit.events(), number)

    async def send_late_replies(self):
        while True:
            await asyncio.sleep(0.25)
            if self.readback_done:
                async with self.visit_lock:
                    # Subsequent calls only drain late LLM replies. They never repeat a question.
                    await self.emit(self.visit.readback(), self.visit.events(), self.reply_turn)

    async def close(self):
        if self.timer:
            self.timer.cancel()
            await asyncio.gather(self.timer, return_exceptions=True)
        await self.speech.close()


@app.post("/api/latency", status_code=204)
def browser_timing(point: BrowserTiming):
    write_timing(point.session, point.turn, point.stage, point.timestamp_ms)
    return Response(status_code=204)


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
                turn.turn_number += 1
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
                if not turn.holding and not turn.hands_free:
                    turn.turn_number += 1
                turn.reply_turn = turn.turn_number
                turn.mark(turn.reply_turn, "commit_sent")
                await prisma.send(COMMIT_MESSAGE)
                turn.holding = False
                turn.queue(turn.pending_speech, turn.reply_turn)
                turn.pending_speech.clear()
                turn.committed = True
                turn.schedule_readback(0.9 if turn.open_utterances else 0.35)
            elif isinstance(event, dict) and event.get("type") == "barge_in":
                await turn.speech.interrupt()


async def send_transcripts(phone: WebSocket, prisma, locale: str, turn: VisitTurn) -> None:
    async for event in prisma:
        if event.get("type") == "error":
            raise RuntimeError("Prisma reported an error")
        if event.get("type") == "speech_start" and event.get("utterance_id"):
            turn.open_utterances.add(event["utterance_id"])
        if event.get("type") == "transcript":
            turn.open_utterances.discard(event.get("utterance_id"))
        if event.get("type") == "transcript" and event.get("text", "").strip():
            if turn.hands_free:
                turn.turn_number += 1
                turn.reply_turn = turn.turn_number
            number = turn.turn_number
            turn.mark(number, "transcript")
            text = event["text"]
            detected = event.get("detected_language_code") or locale
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
            async with turn.visit_lock:
                turn.llm_turns[text] = number
                lines = await asyncio.to_thread(turn.visit.hear, text, detected)
                turn.mark(number, "rules_done")
                await turn.emit(lines, turn.visit.events(), number)
            turn.schedule_readback(0.7 if turn.open_utterances else 0.25)


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
        try:
            session_id = UUID(phone.query_params.get("timing", ""))
        except ValueError:
            session_id = uuid4()
        llm_turns = {}

        def timed_understand(text, visit_type, record):
            number = llm_turns.pop(text, 0)
            try:
                return understand(text, visit_type, record)
            finally:
                if number:
                    write_timing(session_id, number, "llm_done", time.time_ns() / 1e6)

        visit = Visit(start["visit_type"], subject, start["lang"],
                      beneficiary_id=start["beneficiary_id"], understand=timed_understand)
        terms = visit_keyterms(start["visit_type"], start["lang"])
        hands_free = phone.query_params.get("hands_free") == "1"
        # Keep short pauses within a dictated note together. Button release
        # still finalizes immediately via commit; hands-free keeps standard VAD.
        vad = {} if hands_free else {"x_min_silence_ms": 900}
        headers = stt_headers(key, [locale], keyterms=terms, **vad)
        async with PrismaRelay(headers) as prisma:
            timbre = phone.app.state.timbre
            turn = VisitTurn(phone, visit, VisitSpeech(timbre, phone, start["lang"]),
                             hands_free=hands_free,
                             session_id=session_id, llm_turns=llm_turns)
            await turn.emit(visit.start(), visit.events())
            upload = asyncio.create_task(send_audio(phone, prisma, turn))
            download = asyncio.create_task(send_transcripts(phone, prisma, locale, turn))
            followups = asyncio.create_task(turn.send_late_replies())
            try:
                done, _ = await asyncio.wait((upload, download, followups), return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
                if download in done and upload not in done:
                    await phone.close(code=1011, reason="Prisma connection ended")
            finally:
                for task in (upload, download, followups):
                    task.cancel()
                await asyncio.gather(upload, download, followups, return_exceptions=True)
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
