"""Serve the phone page and relay one visit's audio to Prisma."""
from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import datetime as dt
import json
import logging
import os
import time
from contextlib import asynccontextmanager, closing, suppress
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from websockets.exceptions import WebSocketException

from asha import dashboard as board
from asha.context import SUBJECTS
from asha.gnani import COMMIT_MESSAGE, FRAME_BYTES, stt_headers, visit_keyterms
from asha.visit import Visit, now
from asha.danger import DangerChecker, load_lexicon
from asha.speak import Speaker, spoken_sign
from store import default_store
from llm import understand
from stt import PrismaRelay, transcribe_clip
from tts import Timbre, VisitSpeech

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
FRAME_SECONDS = FRAME_BYTES / (16000 * 2)
LANGUAGES = {"hi", "kn", "en"}
VISIT_TYPES = {"anc", "pnc", "hbnc", "hbyc"}
DRAFT_TIMEOUT = 60 * 60
MAX_CLIP_BYTES = 60 * 16000 * 2
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
    app.state.drafts = {}
    key = os.getenv("GNANI_API_KEY", "").strip()
    app.state.timbre = Timbre(key)
    warmup = asyncio.create_task(app.state.timbre.prewarm()) if key else None
    try:
        yield
    finally:
        if warmup:
            warmup.cancel()
            await asyncio.gather(warmup, return_exceptions=True)
        for draft in app.state.drafts.values():
            draft.close()


app = FastAPI(lifespan=lifespan)


class VisitDraft:
    """Keep the live visit independent of any one phone connection."""

    def __init__(self, visit, session_id, llm_turns, identity):
        self.visit = visit
        self.session_id = session_id
        self.llm_turns = llm_turns
        self.identity = identity
        self.events = []
        self.started = False
        self.has_transcript = False
        self.readback_done = False
        self.turn_number = 0
        self.expiry = None
        self.attached = False
        self.synced = set()
        self.answered_offline = set()

    def remember(self, events):
        saved = []
        for event in events:
            if event["type"] == "visit_type":
                event = {**event, "checklist": self.checklist()}
            saved.append({**event, "seq": len(self.events) + 1})
            self.events.append(saved[-1])
        return saved

    def checklist(self):
        return [{"sign": sign, "text": self.visit.speaker.safety_question(sign)}
                for sign in self.visit.danger.guided_questions()]

    def close(self):
        if self.expiry:
            self.expiry.cancel()
        if self.visit.store is not None:
            self.visit.store.close()


class VisitTurn:
    def __init__(self, phone, draft, speech, hands_free):
        self.phone = phone
        self.draft = draft
        self.session_id = draft.session_id
        self.visit_lock = asyncio.Lock()
        self.turn_number = draft.turn_number
        self.reply_turn = draft.turn_number
        self.seen_timings = set()
        self.open_utterances = set()
        self.hands_free = hands_free
        self.visit = draft.visit
        self.speech = speech
        self.holding = False
        self.pending_speech = []
        self.committed = False
        self.timer = None
        self.ended = False
        self.sync_task = None

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
        if self.draft.readback_done:
            return
        if self.timer:
            self.timer.cancel()
        if self.committed and self.draft.has_transcript and not self.holding:
            self.timer = asyncio.create_task(self.readback(delay))

    async def readback(self, delay):
        # Prisma has no commit-complete event in the browser contract. Allow
        # recently finalized VAD segments to arrive before the first readback.
        await asyncio.sleep(delay)
        number = self.reply_turn
        async with self.visit_lock:
            self.draft.readback_done = True
            lines = self.visit.readback()
            await self.emit(lines, self.draft.remember(self.visit.events()), number)

    async def send_late_replies(self):
        while True:
            await asyncio.sleep(0.25)
            if self.draft.readback_done:
                async with self.visit_lock:
                    # Subsequent calls only drain late LLM replies. They never repeat a question.
                    lines = self.visit.readback()
                    await self.emit(lines, self.draft.remember(self.visit.events()), self.reply_turn)

    async def finalize_transcript(self, text, detected, number):
        self.draft.llm_turns[text] = number
        lines = await asyncio.to_thread(self.visit.hear, text, detected)
        self.mark(number, "rules_done")
        self.draft.has_transcript = True
        events = [{"type": "transcript", "text": text, "lang": detected}, *self.visit.events()]
        return lines, self.draft.remember(events)

    async def sync_entry(self, entry, headers):
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or len(entry_id) > 64:
            return
        error = None
        if entry_id not in self.draft.synced:
            try:
                kind = entry.get("kind")
                text = entry.get("text")
                if kind == "audio":
                    encoded = entry.get("pcm")
                    if not isinstance(encoded, str) or len(encoded) > MAX_CLIP_BYTES * 4 // 3:
                        raise ValueError("The recording exceeds 60 seconds.")
                    pcm = base64.b64decode(encoded, validate=True)
                    if not pcm or len(pcm) % 2 or len(pcm) > MAX_CLIP_BYTES:
                        raise ValueError("The recording format is invalid.")
                    text = ". ".join(await transcribe_clip(headers, pcm))
                elif kind == "note":
                    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                        raise ValueError("Enter a note of up to 4,000 characters.")
                elif kind not in ("answer", "save"):
                    raise ValueError("Unknown offline entry.")
                async with self.visit_lock:
                    work = asyncio.create_task(self.apply_entry(entry, text))
                    try:
                        lines, events = await asyncio.shield(work)
                    except asyncio.CancelledError:
                        await work
                        raise
                    await self.emit(lines, events)
            except binascii.Error:
                error = "The recording format is invalid."
            except ValueError as failure:
                error = str(failure)
            except (WebSocketException, OSError, RuntimeError, TimeoutError):
                error = "Sync failed. Try again when speech service is available."
        await self.phone.send_json({"type": "offline_synced", "id": entry_id, "error": error})

    async def apply_entry(self, entry, text):
        if self.visit.saved:
            raise ValueError("This visit was already confirmed.")
        events = []
        if entry["kind"] == "save":
            lines = await asyncio.to_thread(self.visit.confirm)
            if not self.visit.saved:
                raise ValueError("The report could not be saved. Retry sync.")
        elif entry["kind"] == "answer":
            sign, answer = entry.get("sign"), entry.get("answer")
            if sign not in self.visit.danger.guided_questions() or answer not in ("yes", "no", "not sure"):
                raise ValueError("This question is unavailable in the current visit.")
            lines = self.visit.answer_checklist(sign, answer)
            self.draft.answered_offline.add(sign)
        else:
            locale = f"{self.visit.lang}-IN"
            lines = await asyncio.to_thread(self.visit.add_note, text, locale)
            events.append({"type": "transcript", "text": text, "lang": locale})
        self.draft.has_transcript = True
        if not self.draft.readback_done:
            self.draft.readback_done = True
            lines += self.visit.readback()
        events = self.draft.remember([*events, *self.visit.events()])
        self.draft.synced.add(entry["id"])
        return lines, events

    async def close(self):
        if self.sync_task:
            self.sync_task.cancel()
            await asyncio.gather(self.sync_task, return_exceptions=True)
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


def synthetic_patient(beneficiary_id):
    path = BACKEND / "data" / "beneficiaries.json"
    people = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    for person in people:
        if str(person["id"]) == beneficiary_id and person.get("synthetic") is True:
            return person
    raise HTTPException(404, "Synthetic beneficiary not found")


def report_store():
    store = default_store()
    if store is None:
        raise HTTPException(503, "Encrypted report storage is unavailable")
    return closing(store)


@app.get("/api/checklist/{visit_type}")
def checklist(visit_type: Literal["anc", "pnc", "hbnc", "hbyc"], lang: Literal["hi", "kn", "en"] = "hi"):
    speaker = Speaker(lang)
    speaker.say("disclosure")
    return [{"number": number, "sign": sign, "question": speaker.safety_question(sign, number),
             "display_question": speaker.safety_question(sign)}
            for number, sign in enumerate(DangerChecker(visit_type).guided_questions(), 1)]


REPORT_MEASUREMENTS = ("weight_kg", "gestational_month", "hb", "breaths_per_min", "bp", "temperature")


def report_measurements(record):
    for field in REPORT_MEASUREMENTS:
        value = record.get(field)
        if value is not None:
            yield (field, value[1] if field == "temperature" else None), value


def measurement_direction(field, before, after):
    if before == after:
        return "unchanged"
    if field == "bp":
        return "changed"
    if field == "temperature":
        before, after = before[0], after[0]
    return "higher" if after > before else "lower"


def report_sign_changes(receipt, checked_signs):
    current = {row["sign"]: row for row in receipt}
    for sign in dict.fromkeys((*current, *checked_signs)):
        row = current.get(sign, {})
        status = row.get("status", "not_checked")
        last_status, last_date, last_label = checked_signs.get(sign, (None, None, None))
        if status == "present":
            status = {"present": "reported_again", "ruled_out": "new"}.get(last_status, "reported")
        elif last_status != "present":
            continue
        yield {"sign": sign, "label": row.get("label") or last_label or sign, "status": status,
               "previous_date": last_date}


def report_view(visit, previous_date, measurements, signs, seed):
    seed_date = seed.get("date")
    seeded = previous_date is None and bool(seed_date)
    changes = []
    seed_values = dict(report_measurements(seed)) if seed_date else {}
    for key, after in report_measurements(visit["record"]):
        if key in measurements:
            before, date = measurements[key]
            from_seed = False
        elif key in seed_values:
            before, date = seed_values[key], seed_date
            from_seed = True
        else:
            continue
        field, _ = key
        changes.append({"field": field, "before": before, "after": after, "previous_date": date,
                        "seeded_baseline": from_seed, "direction": measurement_direction(field, before, after)})
    sign_changes = list(report_sign_changes(visit["receipt"], signs))
    return {k: v for k, v in visit.items() if k != "transcript"} | {
        "previous_date": seed_date if seeded else previous_date, "seeded_baseline": seeded,
        "changes": changes, "sign_changes": sign_changes,
        "recurring_flags": [row["sign"] for row in sign_changes if row["status"] == "reported_again"],
        "new_flags": [row["sign"] for row in sign_changes if row["status"] == "new"],
    }


def report_views(visits, patient, *, report_id=None):
    """Read newest-first history in chronological order, keeping the last usable evidence."""
    latest_dates, measurements, checked_signs = {}, {}, {}
    for visit in reversed(visits):
        kind, date = visit["visit_type"], visit["saved_at"]
        vitals = measurements.setdefault(kind, {})
        signs = checked_signs.setdefault(kind, {})
        if report_id is None or visit["id"] == report_id:
            seed = (patient.get("last_visit") or {}) if kind == patient.get("visit_type") else {}
            if (seed.get("date") or date) >= date[:10]:
                seed = {}
            yield report_view(visit, latest_dates.get(kind), vitals, signs, seed)
        latest_dates[kind] = date
        for key, value in report_measurements(visit["record"]):
            vitals[key] = value, date
        for row in visit["receipt"]:
            if row["status"] in ("present", "ruled_out"):
                signs[row["sign"]] = row["status"], date, row.get("label")


def confirmed_report(store, session):
    visit_id = store.report_id(str(session))
    visit = store.load_visit(visit_id) if visit_id else None
    if not visit or visit["status"] != "saved":
        raise HTTPException(404, "Confirmed report not found")
    return visit


@app.get("/api/visit-report/{session}")
def visit_report(session: UUID, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with report_store() as store:
        visit = confirmed_report(store, session)
        patient = synthetic_patient(visit["beneficiary_id"])
        earlier = [row for row in store.history(visit["beneficiary_id"])
                   if row["id"] < visit["id"] and row["visit_type"] == visit["visit_type"]]
        return next(report_views([visit, *earlier], patient, report_id=visit["id"]))


@app.post("/api/visit-report/{session}/file")
def file_visit_report(session: UUID, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with report_store() as store:
        visit = confirmed_report(store, session)
        synthetic_patient(visit["beneficiary_id"])
        if not store.file_report(visit["id"], str(session), now()):
            raise HTTPException(409, "The visit was undone or changed")
        return {"beneficiary_id": visit["beneficiary_id"], "visit_id": visit["id"]}


@app.get("/api/patients/{beneficiary_id}/history")
def patient_history(beneficiary_id: str, response: Response):
    response.headers["Cache-Control"] = "no-store"
    patient = synthetic_patient(beneficiary_id)
    with report_store() as store:
        return list(reversed(list(report_views(store.history(beneficiary_id), patient))))


def synthetic_patients():
    path = BACKEND / "data" / "beneficiaries.json"
    people = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    return [person for person in people if person.get("synthetic") is True]


def with_sign_names(view):
    """Add {sign: {hi, kn, en}} for every danger sign named anywhere in the view, for the page language."""
    known, found = load_lexicon().signs, set()

    def walk(value):
        if isinstance(value, dict):
            if value.get("sign") in known:
                found.add(value["sign"])
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(view)
    return view | {"sign_names": {sign: {lang: spoken_sign(sign, lang) for lang in ("hi", "kn", "en")}
                                  for sign in sorted(found)}}


def dashboard_inputs(store):
    patients = synthetic_patients()
    histories = {p["id"]: store.history(p["id"]) for p in patients}
    return patients, histories, store.referrals(), store.marks()


@app.get("/api/dashboard")
def dashboard_view(response: Response):
    response.headers["Cache-Control"] = "no-store"
    with report_store() as store:
        return with_sign_names(board.dashboard(*dashboard_inputs(store), dt.date.today()))


@app.get("/api/patients/{beneficiary_id}")
def patient_view(beneficiary_id: str, response: Response):
    response.headers["Cache-Control"] = "no-store"
    patient = synthetic_patient(beneficiary_id)
    with report_store() as store:
        visits = store.history(beneficiary_id)
        referrals, marks = store.referrals(), store.marks()
        summary = board.patient_summary(patient, visits, referrals, marks, dt.date.today())
        views = list(report_views(visits, patient))      # oldest first
        audit = {v["id"]: store.audit(v["id"]) for v in visits}
    for view in views:
        view["audit"] = audit[view["id"]] + [
            {"at": s["at"], "kind": f"referral_{s['step']}", "sign": key.split(":", 2)[2], "by": "anm"}
            for key, steps in referrals.items() if key.startswith(f"flag:{view['id']}:") for s in steps]
        view["audit"].sort(key=lambda row: row["at"])
    return with_sign_names(summary | {"visits": list(reversed(views)), "timeline": board.timeline(patient, visits)})


class ReferralStep(BaseModel):
    key: str = Field(max_length=120)
    step: Literal["referred", "reached_phc", "closed"]


@app.post("/api/referrals")
def referral_step(change: ReferralStep, response: Response):
    """The ANM moves a danger flag one step along. Steps never skip and never go back."""
    response.headers["Cache-Control"] = "no-store"
    with report_store() as store:
        view = board.dashboard(*dashboard_inputs(store), dt.date.today())
        flag = next((f for f in view["flags"] if f["key"] == change.key), None)
        if flag is None:
            raise HTTPException(404, "Open danger flag not found")
        if board.next_step(flag["step"]) != change.step:
            raise HTTPException(409, "That step is not next for this flag")
        store.add_referral_step(change.key, change.step, now())
    return {"key": change.key, "step": change.step}


class ReviewMark(BaseModel):
    key: str = Field(max_length=120)
    kind: Literal["reported", "checked"]


@app.post("/api/review-marks")
def review_mark(mark: ReviewMark, response: Response):
    response.headers["Cache-Control"] = "no-store"
    with report_store() as store:
        view = board.dashboard(*dashboard_inputs(store), dt.date.today())
        pending = {i["key"] for i in view["report"]} if mark.kind == "reported" else {i["key"] for i in view["checks"]}
        if mark.key not in pending:
            raise HTTPException(404, "Nothing waiting with that key")
        store.mark(mark.key, mark.kind, now())
    return {"key": mark.key, "kind": mark.kind}


async def send_audio(phone: WebSocket, prisma, turn: VisitTurn, headers) -> None:
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
            if not isinstance(event, dict):
                continue
            if event.get("type") == "end_visit":
                turn.ended = True
                await phone.close()
                return
            if event.get("type") == "ping":
                await phone.send_json({"type": "pong"})
            elif event.get("type") == "offline_entry":
                if not turn.sync_task or turn.sync_task.done():
                    turn.sync_task = asyncio.create_task(turn.sync_entry(event, headers))
            elif event.get("type") == "commit":
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
            elif event.get("type") == "barge_in":
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
            async with turn.visit_lock:
                work = asyncio.create_task(turn.finalize_transcript(text, detected, number))
                try:
                    lines, events = await asyncio.shield(work)
                except asyncio.CancelledError:
                    # A final transcript already received from Prisma belongs to the draft.
                    await work
                    raise
                await turn.emit(lines, events, number)
            latency = event.get("latency")
            if isinstance(latency, (int, float)):
                await phone.send_json({"type": "latency", "ms": latency})
            if turn.hands_free:
                turn.committed = True
            turn.schedule_readback(0.7 if turn.open_utterances else 0.25)


def open_draft(start, session_id, identity):
    llm_turns = {}

    def timed_understand(text, visit_type, record):
        number = llm_turns.pop(text, 0)
        try:
            return understand(text, visit_type, record)
        finally:
            if number:
                write_timing(session_id, number, "llm_done", time.time_ns() / 1e6)

    visit = Visit(start["visit_type"], SUBJECTS[start["visit_type"]], start["lang"],
                  beneficiary_id=start["beneficiary_id"], understand=timed_understand,
                  report_session=str(session_id))
    return VisitDraft(visit, session_id, llm_turns, identity)


def expire_draft(drafts, token):
    drafts.pop(token).close()


@app.websocket("/ws")
async def visit_socket(phone: WebSocket) -> None:
    await phone.accept()
    draft = turn = None
    token = None
    drafts = phone.app.state.drafts
    try:
        start = await asyncio.wait_for(phone.receive_json(), timeout=15)
        if (not isinstance(start, dict) or start.get("type") not in {"start_visit", "resume_visit"}
                or start.get("lang") not in LANGUAGES or start.get("visit_type") not in VISIT_TYPES
                or not isinstance(start.get("beneficiary_id"), str) or not start["beneficiary_id"]):
            await phone.close(code=1008, reason="Expected a valid start_visit")
            return
        key = os.getenv("GNANI_API_KEY", "").strip()
        if not key:
            await phone.close(code=4403, reason="GNANI_API_KEY is missing on the server")
            return
        try:
            session_id = UUID(phone.query_params.get("timing", ""))
        except ValueError:
            session_id = uuid4()
        token = UUID(start["draft_token"]) if "draft_token" in start else None
        after = start.get("after_event", 0)
        if type(after) is not int or after < 0:
            await phone.close(code=1008, reason="Invalid visit progress")
            return
        identity = (session_id, start["beneficiary_id"], start["visit_type"], start["lang"])
        existing = drafts.get(token)
        if existing is None and start["type"] == "resume_visit":
            await phone.close(code=4404, reason="Visit draft expired or the server restarted")
            return
        if existing and (existing.identity != identity or after > len(existing.events)):
            await phone.close(code=1008, reason="Visit draft does not match this session")
            return
        if existing and existing.attached:
            await phone.close(code=4409, reason="Previous connection is closing")
            return
        draft = existing or open_draft(start, session_id, identity)
        draft.attached = True
        if token:
            drafts[token] = draft
            if draft.expiry:
                draft.expiry.cancel()
                draft.expiry = None
        visit = draft.visit
        locale = f"{visit.lang}-IN"
        terms = visit_keyterms(visit.visit_type, visit.lang)
        hands_free = phone.query_params.get("hands_free") == "1"
        # Keep short pauses within a dictated note together. Button release
        # still finalizes immediately via commit; hands-free keeps standard VAD.
        vad = {} if hands_free else {"x_min_silence_ms": 900}
        headers = stt_headers(key, [locale], keyterms=terms, **vad)
        async with PrismaRelay(headers) as prisma:
            timbre = phone.app.state.timbre
            turn = VisitTurn(phone, draft, VisitSpeech(timbre, phone, visit.lang), hands_free)
            tasks = []
            try:
                resumed = draft.started
                if not draft.has_transcript:
                    lines = visit.start()
                    draft.started = True
                else:
                    lines = visit.resume() if draft.readback_done else []
                draft.remember(visit.events())
                for event in draft.events[after:]:
                    await phone.send_json(event)
                if token:
                    await phone.send_json({"type": "visit_ready", "resumed": resumed,
                                           "turn": draft.turn_number, "speaking_next": bool(lines),
                                           "saved": visit.saved,
                                           "answered_offline": sorted(draft.answered_offline),
                                           "checklist": draft.checklist()})
                turn.queue(lines, 0)
                if resumed and draft.has_transcript and not draft.readback_done:
                    turn.committed = True
                    turn.schedule_readback(0.25)
                upload = asyncio.create_task(send_audio(phone, prisma, turn, headers))
                download = asyncio.create_task(send_transcripts(phone, prisma, locale, turn))
                tasks = [upload, download, asyncio.create_task(turn.send_late_replies())]
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
                if download in done and upload not in done:
                    await phone.close(code=1011, reason="Prisma connection ended")
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await turn.close()
    except WebSocketDisconnect:
        pass
    except (ValueError, KeyError, TypeError):
        with suppress(RuntimeError, WebSocketDisconnect):
            await phone.close(code=1008, reason="Invalid WebSocket message")
    except (WebSocketException, OSError, RuntimeError, TimeoutError):
        with suppress(RuntimeError, WebSocketDisconnect):
            await phone.close(code=1011, reason="Speech connection failed. Try again.")
    finally:
        if draft:
            draft.attached = False
            if turn:
                draft.turn_number = turn.turn_number
            if not token:
                draft.close()
            elif turn and turn.ended:
                expire_draft(drafts, token)
            else:
                draft.expiry = asyncio.get_running_loop().call_later(
                    DRAFT_TIMEOUT, expire_draft, drafts, token)


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
