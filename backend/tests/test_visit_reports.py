from uuid import uuid4

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


def save(store, date, *, record=None, signs=None, session=None, patient="4127", kind="anc"):
    return store.save_visit(
        beneficiary_id=patient, visit_type=kind, lang="en", saved_at=date, record=record or {},
        transcript=[{"text": "synthetic transcript"}], flags=[], session_key=session,
        receipt=[{"sign": sign, "label": sign.capitalize(), "status": status}
                 for sign, status in (signs or {}).items()],
    )


def test_report_compares_last_usable_measurements_and_sign_checks(visits):
    store, client = visits
    save(store, "2026-11-01", record={"weight_kg": 52, "hb": 10, "temperature": [98, "F"]},
         signs={"repeat": "present", "skipped": "present", "denied": "present", "new": "ruled_out",
                "unknown": "not_checked", "omitted": "present"})
    earlier_session = str(uuid4())
    saved = save(store, "2026-11-08", record={"hb": 11, "temperature": [37, "C"]},
                 signs={"repeat": "not_checked", "skipped": "not_checked"}, session=earlier_session)
    assert store.file_report(saved, earlier_session, "2026-11-08")
    save(store, "2026-11-09", patient="4381", record={"weight_kg": 60})
    save(store, "2026-11-10", kind="pnc", record={"weight_kg": 60})
    save(store, "2026-11-11", record={"weight_kg": 60}, session=str(uuid4()))
    undone = save(store, "2026-11-12", record={"weight_kg": 60})
    store.mark_undone(undone, "2026-11-12")

    session = str(uuid4())
    visit_id = save(store, "2026-11-17", record={"weight_kg": 54, "hb": 11, "temperature": [97, "F"]},
                    signs={"repeat": "present", "skipped": "not_checked", "denied": "ruled_out",
                           "new": "present", "unknown": "present"}, session=session)
    save(store, "2026-11-19", record={"weight_kg": 55})
    response = client.get(f"/api/visit-report/{session}")
    assert response.status_code == 200
    report = response.json()
    assert report["previous_date"] == "2026-11-08"
    assert "transcript" not in report
    assert {change["field"]: (change["before"], change["after"], change["direction"], change["previous_date"])
            for change in report["changes"]} == {
        "weight_kg": (52, 54, "higher", "2026-11-01"),
        "hb": (11, 11, "unchanged", "2026-11-08"),
        "temperature": ([98, "F"], [97, "F"], "lower", "2026-11-01"),
    }
    assert {row["sign"]: (row["status"], row["previous_date"]) for row in report["sign_changes"]} == {
        "repeat": ("reported_again", "2026-11-01"),
        "skipped": ("not_checked", "2026-11-01"),
        "denied": ("ruled_out", "2026-11-01"),
        "new": ("new", "2026-11-01"),
        "unknown": ("reported", None),
        "omitted": ("not_checked", "2026-11-01"),
    }

    assert client.post(f"/api/visit-report/{session}/file").status_code == 200
    history = client.get("/api/patients/4127/history").json()
    assert next(row for row in history if row["id"] == visit_id) == report


@pytest.mark.parametrize("kind, expected", [("anc", "2026-10-24"), ("pnc", None)])
def test_first_visit_only_compares_to_matching_synthetic_baseline(visits, kind, expected):
    store, client = visits
    session = str(uuid4())
    save(store, "2026-11-17", kind=kind, record={"weight_kg": 51}, session=session,
         signs={"fever": "present"})
    report = client.get(f"/api/visit-report/{session}").json()
    assert report["previous_date"] == expected
    assert report["seeded_baseline"] is bool(expected)
    assert report["sign_changes"][0]["status"] == "reported"
    if expected:
        assert report["changes"] == [{
            "field": "weight_kg", "before": 52, "after": 51, "direction": "lower",
            "previous_date": expected, "seeded_baseline": True,
        }]
    else:
        assert report["changes"] == []
