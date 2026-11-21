import sqlite3

import pytest
from cryptography.fernet import Fernet

from asha.visit import Visit
from store import Store

FLAG = {"sign": "anc_bleeding", "quote": "khoon aa raha tha", "at": "2026-11-21T10:00:00", "by": "rules"}


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "v.db", Fernet.generate_key())
    yield s
    s.close()


def save(store, **kw):
    args = dict(beneficiary_id="4127", visit_type="anc", lang="hi", saved_at="2026-11-21T10:01:00",
                record={"weight_kg": 52.0}, transcript=[{"text": "wajan baavan kilo"}],
                receipt=[{"sign": "anc_bleeding", "status": "present"}], flags=[FLAG])
    return store.save_visit(**{**args, **kw})


def test_save_and_load_round_trip(store):
    vid = save(store)
    v = store.load_visit(vid)
    assert v["record"] == {"weight_kg": 52.0} and v["status"] == "saved"
    assert v["transcript"][0]["text"] == "wajan baavan kilo"
    assert store.audit(vid) == [
        {"at": FLAG["at"], "kind": "flag", "sign": "anc_bleeding", "by": "rules", "quote": FLAG["quote"]},
        {"at": "2026-11-21T10:01:00", "kind": "saved", "sign": None, "by": None, "quote": None}]


def test_her_words_are_not_readable_on_disk(store):
    save(store)
    raw = (store.path).read_bytes()
    for secret in (b"wajan", b"khoon", b"52.0"):
        assert secret not in raw


def test_wrong_key_cannot_read(store, tmp_path):
    vid = save(store)
    other = Store(tmp_path / "v.db", Fernet.generate_key())
    with pytest.raises(ValueError, match="DB_KEY"):
        other.load_visit(vid)


def test_bad_key_is_rejected_clearly(tmp_path):
    with pytest.raises(ValueError, match="Fernet"):
        Store(tmp_path / "v.db", "not-a-key")


def test_undo_keeps_row_for_audit(store):
    vid = save(store)
    store.mark_undone(vid, "2026-11-21T10:01:03")
    assert store.load_visit(vid)["status"] == "undone"
    assert store.audit(vid)[-1]["kind"] == "undone"


# ---------- Visit writes to the store ----------

def visit(store, clock):
    v = Visit("anc", subject="mother", lang="hi", use_llm=False, store=store, beneficiary_id="4127",
              clock=clock)
    v.start()
    return v


def test_visit_saves_record_transcript_receipt_and_flag(store):
    v = visit(store, lambda: 0.0)
    v.hear("wajan baavan kilo, thoda khoon aa raha hai")
    v.hear("record pakka")
    saved = store.load_visit(v.visit_id)
    assert saved["beneficiary_id"] == "4127" and saved["record"]["weight_kg"] == 52.0
    assert [t["text"] for t in saved["transcript"]] == ["wajan baavan kilo, thoda khoon aa raha hai",
                                                       "record pakka"]
    assert any(r["status"] == "present" for r in saved["receipt"])
    flags = [a for a in store.audit(v.visit_id) if a["kind"] == "flag"]
    assert flags and flags[0]["by"] == "rules" and "khoon" in flags[0]["quote"]


def test_visit_undo_marks_saved_row_undone(store):
    t = [0.0]
    v = visit(store, lambda: t[0])
    v.hear("wajan baavan kilo")
    v.hear("record pakka")
    vid = v.visit_id
    t[0] = 2.0
    v.hear("ruko")
    assert store.load_visit(vid)["status"] == "undone" and v.visit_id is None


def test_failed_disk_write_never_says_saved(store):
    store.db.close()                         # every write now fails
    v = visit(store, lambda: 0.0)
    lines = v.hear("record pakka")
    assert not v.saved and "save nahi hua" in lines[-1]
    assert all(e["type"] != "saved" for e in v.events())


def test_llm_flag_is_audited_as_llm(store):
    v = Visit("hbnc", subject="newborn", lang="hi", use_llm=True, store=store, beneficiary_id="7409",
              understand=lambda *a: {"ok": True, "fields": {}, "evidence": {}, "unsure": [],
                                     "danger_signs": [{"id": "nb_poor_feeding", "status": "present",
                                                       "evidence": "subah se kuch nahi liya"}]})
    v.start()
    v.hear("subah se kuch nahi liya")
    v.followup()
    v.hear("record pakka")
    flags = [a for a in store.audit(v.visit_id) if a["kind"] == "flag"]
    assert [(f["sign"], f["by"]) for f in flags] == [("nb_poor_feeding", "llm")]


def test_history_only_includes_filed_or_legacy_visits_and_skips_undone(tmp_path):
    store = Store(tmp_path / "history.db", Fernet.generate_key())
    def save(patient, weight, session=None):
        return store.save_visit(beneficiary_id=patient, visit_type="anc", lang="hi",
                                saved_at="2026-11-21", record={"weight_kg": weight},
                                transcript=[], receipt=[], flags=[], session_key=session)
    try:
        old = save("4127", 51)
        save("4381", 60)
        current = save("4127", 52, "first-session")
        assert [row["id"] for row in store.history("4127")] == [old]
        assert store.report_id("first-session") == current
        assert store.previous_visit(store.load_visit(current))["id"] == old
        assert not store.file_report(current, "other-session", "2026-11-21")
        assert store.file_report(current, "first-session", "2026-11-21")
        assert store.file_report(current, "first-session", "2026-11-21")
        assert [row["id"] for row in store.history("4127")] == [current, old]
        store.mark_undone(current, "2026-11-21")
        assert store.report_id("first-session") is None
        assert not store.file_report(current, "first-session", "2026-11-21")
        assert [row["id"] for row in store.history("4127")] == [old]
    finally:
        store.close()


def test_referral_steps_are_kept_in_order(store):
    store.add_referral_step("flag:1:anc_bleeding", "referred", "2026-11-21T11:00:00")
    store.add_referral_step("flag:1:anc_bleeding", "reached_phc", "2026-11-21T15:00:00")

    assert [s["step"] for s in store.referrals()["flag:1:anc_bleeding"]] == ["referred", "reached_phc"]


def test_a_review_mark_is_written_once(store):
    store.mark("flag:1:anc_bleeding", "reported", "2026-11-21T11:00:00")
    store.mark("flag:1:anc_bleeding", "reported", "2026-11-22T11:00:00")

    assert store.marks() == {"flag:1:anc_bleeding": {"kind": "reported", "at": "2026-11-21T11:00:00"}}
