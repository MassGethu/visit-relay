import pytest
from cryptography.fernet import Fernet

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from app import app
from store import Store


@pytest.fixture
def visits(monkeypatch, tmp_path):
    path = tmp_path / "visits.db"
    key = Fernet.generate_key()
    monkeypatch.setenv("DB_KEY", key.decode())
    monkeypatch.setenv("DB_PATH", str(path))
    store = Store(path, key)
    try:
        yield store, TestClient(app)
    finally:
        store.close()


def save_flagged(store, patient="4127"):
    return store.save_visit(
        beneficiary_id=patient, visit_type="anc", lang="en", saved_at="2026-11-20T10:00:00",
        record={"weight_kg": 54.0}, transcript=[{"text": "synthetic"}],
        receipt=[{"sign": "anc_vaginal_bleeding", "label": "Bleeding", "status": "present", "quote": "synthetic"}],
        flags=[{"sign": "anc_vaginal_bleeding", "quote": "synthetic", "at": "2026-11-20T10:00:00", "by": "rules"}])


def test_dashboard_lists_open_flags_and_every_synthetic_patient_for_search(visits):
    store, client = visits
    visit_id = save_flagged(store)

    view = client.get("/api/dashboard").json()

    assert [f["key"] for f in view["flags"]] == [f"flag:{visit_id}:anc_vaginal_bleeding"]
    assert view["tags"]["danger"] == 1 and len(view["patients"]) == 15


def test_referral_steps_must_go_in_order_and_close_the_flag(visits):
    store, client = visits
    key = f"flag:{save_flagged(store)}:anc_vaginal_bleeding"

    skipped = client.post("/api/referrals", json={"key": key, "step": "closed"})
    for step in ("referred", "reached_phc", "closed"):
        assert client.post("/api/referrals", json={"key": key, "step": step}).status_code == 200

    assert skipped.status_code == 409
    assert client.get("/api/dashboard").json()["flags"] == []
    assert client.post("/api/referrals", json={"key": key, "step": "closed"}).status_code == 404


def test_reporting_a_flag_takes_it_off_the_report_list(visits):
    store, client = visits
    key = f"flag:{save_flagged(store)}:anc_vaginal_bleeding"

    assert client.post("/api/review-marks", json={"key": key, "kind": "reported"}).status_code == 200
    assert client.get("/api/dashboard").json()["report"] == []
    assert client.post("/api/review-marks", json={"key": "flag:99:x", "kind": "reported"}).status_code == 404


def test_patient_view_has_trend_audit_and_no_transcript(visits):
    store, client = visits
    key = f"flag:{save_flagged(store)}:anc_vaginal_bleeding"
    client.post("/api/referrals", json={"key": key, "step": "referred"})

    view = client.get("/api/patients/4127").json()

    assert view["timeline"]["weight_kg"]["points"][-1]["value"] == 54.0
    assert [a["kind"] for a in view["visits"][0]["audit"]] == ["flag", "saved", "referral_referred"]
    assert "transcript" not in view["visits"][0]
    assert client.get("/api/patients/nope").status_code == 404


def test_sign_names_come_in_every_page_language(visits):
    store, client = visits
    save_flagged(store)

    names = client.get("/api/dashboard").json()["sign_names"]

    assert set(names["anc_vaginal_bleeding"]) == {"hi", "kn", "en"}
