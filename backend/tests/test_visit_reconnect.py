"""Exercise the phone WebSocket with synthetic Prisma transcripts."""
import asyncio
from contextlib import asynccontextmanager
from threading import Event
from uuid import uuid4

import pytest

pytest.importorskip("fastapi")
from cryptography.fernet import Fernet
from starlette.websockets import WebSocketDisconnect

import app as relay
from asha.visit import Visit
from store import Store


class PhoneSocket:
    def __init__(self, session, start, hands_free):
        self.app = relay.app
        self.query_params = {"timing": str(session), "hands_free": str(int(hands_free))}
        self.start = start
        self.incoming = asyncio.Queue()
        self.outgoing = asyncio.Queue()
        self.spoken = asyncio.Queue()
        self.disconnected = False

    async def accept(self):
        pass

    async def receive_json(self):
        return self.start

    async def receive(self):
        return await self.incoming.get()

    async def send_json(self, event):
        if self.disconnected:
            raise WebSocketDisconnect(1006)
        self.outgoing.put_nowait(event)

    async def close(self, code=1000, reason=None):
        await self.send_json({"type": "close", "code": code})

    def disconnect(self):
        self.disconnected = True
        self.incoming.put_nowait({"type": "websocket.disconnect"})

    def send_entry(self, entry):
        self.incoming.put_nowait({"type": "websocket.receive",
                                  "text": relay.json.dumps({"type": "offline_entry", **entry})})

    async def next_event(self):
        return await asyncio.wait_for(self.outgoing.get(), 2)

    async def next_speech(self):
        return await asyncio.wait_for(self.spoken.get(), 2)

    async def receive_until(self, event_type):
        while (event := await self.next_event())["type"] != event_type:
            assert event["type"] != "close", event
        return event


@pytest.fixture
def phone(monkeypatch, tmp_path):
    incoming = asyncio.Queue()

    class Prisma:
        def __init__(self, headers):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def send(self, message):
            pass

        async def __aiter__(self):
            while True:
                yield await incoming.get()

    class Speech:
        def __init__(self, timbre, phone, lang):
            self.phone = phone

        def queue(self, lines, **kwargs):
            self.phone.spoken.put_nowait(lines)

        async def close(self):
            pass

    async def prewarm(self):
        pass

    db, key = tmp_path / "visits.db", Fernet.generate_key()
    monkeypatch.setenv("GNANI_API_KEY", "fake-gnani-key")
    monkeypatch.setattr(relay, "PrismaRelay", Prisma)
    monkeypatch.setattr(relay, "VisitSpeech", Speech)
    monkeypatch.setattr(relay.Timbre, "prewarm", prewarm)
    monkeypatch.setattr(relay, "Visit", lambda *args, **kwargs: Visit(*args, **kwargs, store=Store(db, key)))
    monkeypatch.setattr(relay, "understand", lambda *args: {"ok": False})
    monkeypatch.setattr(relay, "TIMING_FILE", tmp_path / "latency.csv")
    session = uuid4()
    start = {"type": "start_visit", "beneficiary_id": "synthetic", "visit_type": "anc",
             "lang": "hi", "draft_token": str(uuid4())}

    def dictate(text):
        incoming.put_nowait({"type": "transcript", "text": text})

    @asynccontextmanager
    async def connect(request, hands_free=True):
        socket = PhoneSocket(session, request, hands_free)
        task = asyncio.create_task(relay.visit_socket(socket))
        try:
            yield socket
        finally:
            socket.disconnect()
            await asyncio.wait_for(task, 2)

    return connect, start, dictate


def test_reconnect_restores_visit_and_continues_checklist(phone):
    connect, start, dictate = phone
    resume = {**start, "type": "resume_visit"}

    async def exercise():
        async with relay.lifespan(relay.app):
            async with connect(start) as socket:
                assert not (await socket.receive_until("visit_ready"))["resumed"]
                socket.incoming.put_nowait({"type": "websocket.receive", "text": '{"type":"ping"}'})
                assert await socket.receive_until("pong") == {"type": "pong"}
                dictate("wajan baavan kilo, I am done.")
                weight = await socket.receive_until("record")
                first = await socket.receive_until("question")
                dictate("no, I am done.")
                second = await socket.receive_until("question")
                assert second["text"] != first["text"]

            async with connect({**resume, "after_event": weight["seq"]}) as socket:
                assert await socket.receive_until("question") == first
                assert (await socket.receive_until("transcript"))["text"] == "no"
                assert await socket.receive_until("question") == second
                assert (await socket.receive_until("question"))["text"] == second["text"]
                assert (await socket.receive_until("visit_ready"))["resumed"]
                dictate("hb das")
                assert (await socket.receive_until("record"))["fields"] == {"weight_kg": 52.0, "hb": 10.0}
                dictate("record pakka")
                saved = await socket.receive_until("saved")

            async with connect({**resume, "after_event": saved["seq"]}) as socket:
                assert (await socket.next_event())["type"] == "visit_ready"
                draft, = relay.app.state.drafts.values()
                visit = draft.visit
                assert visit.saved
                assert visit.store.report_id(visit.report_session) == visit.visit_id
                socket.incoming.put_nowait({"type": "websocket.receive", "text": '{"type":"end_visit"}'})
                assert (await socket.next_event())["type"] == "close"

            async with connect(resume) as socket:
                assert await socket.next_event() == {"type": "close", "code": 4404}

    asyncio.run(exercise())


def test_reconnect_replays_alert_from_transcript_processed_during_disconnect(phone, monkeypatch):
    connect, start, dictate = phone
    hear = Visit.hear
    finish = Event()

    async def exercise():
        loop = asyncio.get_running_loop()
        started = asyncio.Event()

        def slow_hear(visit, text, lang):
            loop.call_soon_threadsafe(started.set)
            assert finish.wait(2)
            return hear(visit, text, lang)

        monkeypatch.setattr(Visit, "hear", slow_hear)
        async with relay.lifespan(relay.app):
            async with connect(start) as socket:
                await socket.receive_until("visit_ready")
                dictate("thoda khoon aa raha hai")
                await asyncio.wait_for(started.wait(), 2)
                socket.disconnect()
                finish.set()

            async with connect({**start, "type": "resume_visit"}) as socket:
                assert (await socket.receive_until("transcript"))["text"] == "thoda khoon aa raha hai"
                assert (await socket.receive_until("alert"))["sign"] == "anc_vaginal_bleeding"
                assert (await socket.receive_until("visit_ready"))["resumed"]

    asyncio.run(exercise())


def test_hands_free_waits_for_cue_and_preserves_safety_alerts(phone):
    connect, start, dictate = phone

    async def exercise():
        async with relay.lifespan(relay.app):
            async with connect(start) as socket:
                await socket.receive_until("visit_ready")
                draft, = relay.app.state.drafts.values()
                speaker = draft.visit.speaker
                ready = speaker.say("hands_free_ready")
                assert await socket.next_speech() == [
                    speaker.say("disclosure"), speaker.say("hands_free_intro"), ready,
                ]
                dictate("wajan baavan kilo")
                assert (await socket.receive_until("record"))["fields"] == {"weight_kg": 52.0}
                dictate("thoda khoon aa raha hai")
                alert = await socket.receive_until("alert")
                assert alert["sign"] == "anc_vaginal_bleeding"
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(socket.spoken.get(), 0.4)
                assert not draft.readback_done

            async with connect({**start, "type": "resume_visit"}) as socket:
                assert not (await socket.receive_until("visit_ready"))["speaking_next"]
                dictate("hb das, I am done.")
                assert (await socket.receive_until("transcript"))["text"] == "hb das"
                first = await socket.receive_until("question")
                assert await socket.next_speech() == [speaker.alert(alert["sign"]), first["text"], ready]
                assert [row["text"] for row in draft.visit.transcript] == [
                    "wajan baavan kilo", "thoda khoon aa raha hai", "hb das",
                ]
                dictate("no")
                await socket.receive_until("transcript")
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(socket.spoken.get(), 0.1)
                dictate("katham")
                reply = await socket.next_speech()
                assert len(reply) == 2 and reply[-1] == ready
                assert draft.visit.transcript[-1]["text"] == "no"

    asyncio.run(exercise())


def test_push_to_talk_uses_button_release_without_a_spoken_cue(phone):
    connect, start, dictate = phone

    async def exercise():
        async with relay.lifespan(relay.app):
            async with connect(start, hands_free=False) as socket:
                await socket.receive_until("visit_ready")
                draft, = relay.app.state.drafts.values()
                assert await socket.next_speech() == [draft.visit.speaker.say("disclosure")]
                socket.incoming.put_nowait({"type": "websocket.receive", "text": '{"type":"commit"}'})
                dictate("wajan baavan kilo")
                assert (await socket.receive_until("transcript"))["text"] == "wajan baavan kilo"
                question = await socket.receive_until("question")
                assert await socket.next_speech() == [question["text"]]

    asyncio.run(exercise())


def test_offline_entries_sync_and_retry_without_duplicates(phone, monkeypatch):
    connect, start, _ = phone
    note = {"id": "note", "kind": "note", "text": "wajan baavan kilo"}
    recording = {"id": "audio", "kind": "audio", "pcm": "AAA="}

    async def transcribe(headers, pcm):
        assert pcm == b"\0\0"
        return ["hb das"]

    monkeypatch.setattr(relay, "transcribe_clip", transcribe)

    async def exercise():
        async with relay.lifespan(relay.app):
            async with connect(start) as socket:
                ready = await socket.receive_until("visit_ready")
                assert ready["checklist"]
                socket.send_entry(note)
                assert (await socket.receive_until("record"))["fields"] == {"weight_kg": 52.0}
                assert (await socket.receive_until("offline_synced"))["error"] is None

            async with connect({**start, "type": "resume_visit"}) as socket:
                await socket.receive_until("visit_ready")
                socket.send_entry(note)
                assert (await socket.next_event())["type"] == "offline_synced"
                socket.send_entry(recording)
                assert (await socket.receive_until("record"))["fields"]["hb"] == 10.0
                assert (await socket.receive_until("offline_synced"))["error"] is None
                socket.send_entry({"id": "answer", "kind": "answer", "sign": "anc_vaginal_bleeding", "answer": "yes"})
                assert (await socket.receive_until("alert"))["sign"] == "anc_vaginal_bleeding"
                assert (await socket.receive_until("offline_synced"))["error"] is None
                socket.send_entry({"id": "save", "kind": "save"})
                await socket.receive_until("saved")
                assert (await socket.receive_until("offline_synced"))["error"] is None
                draft, = relay.app.state.drafts.values()
                assert [item["text"] for item in draft.visit.transcript].count(note["text"]) == 1

    asyncio.run(exercise())
