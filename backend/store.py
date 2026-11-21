"""Saved visits: SQLite, with everything she said encrypted at rest (Fernet, key = DB_KEY in .env).

Plain columns are only what is needed to find a row: beneficiary ID, visit type, language, times,
sign IDs and statuses. The record, the transcript, the receipt and every quote are encrypted.
The audit table keeps every danger flag (who flagged it, when, her words) and every save / undo.
scripts/delete_all.py wipes the database after judging.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
DEFAULT_DB = BACKEND / "data" / "visits.db"     # *.db is gitignored

SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    beneficiary_id TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    lang TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'saved',        -- 'saved' | 'undone'
    record BLOB NOT NULL,
    transcript BLOB NOT NULL,
    receipt BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS visit_reports (
    visit_id INTEGER PRIMARY KEY REFERENCES visits(id),
    session_key TEXT UNIQUE NOT NULL,
    filed_at TEXT
);
CREATE INDEX IF NOT EXISTS visits_patient_history ON visits (beneficiary_id, visit_type, id);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL REFERENCES visits(id),
    at TEXT NOT NULL,
    kind TEXT NOT NULL,   -- 'flag' | 'concern_noted' | 'concern_flagged' | 'visit_switch' | 'saved' | 'undone'
    sign TEXT,
    flagged_by TEXT,      -- 'rules' | 'llm' | 'asha' (worker concern) | 'voice' / 'screen' (visit switch)
    quote BLOB
);
CREATE TABLE IF NOT EXISTS referrals (    -- each step the ANM takes on a danger flag, append-only
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_key TEXT NOT NULL,               -- "flag:<visit_id>:<sign>"
    step TEXT NOT NULL,                   -- 'referred' | 'reached_phc' | 'closed'
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_marks ( -- "reported to ANM" / "double-checked", one per item
    item_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                   -- 'reported' | 'checked'
    at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path, key: str | bytes):
        try:
            self.fernet = Fernet(key)
        except (ValueError, TypeError) as e:
            raise ValueError("DB_KEY is not a valid Fernet key (make one with Fernet.generate_key())") from e
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()                 # Visit may save from a worker thread
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    # ---------- encryption ----------

    def _seal(self, value) -> bytes:
        return self.fernet.encrypt(json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def _open(self, blob: bytes | None):
        if blob is None:
            return None
        try:
            return json.loads(self.fernet.decrypt(blob))
        except InvalidToken as e:
            raise ValueError("cannot decrypt: DB_KEY differs from the key the data was saved with") from e

    # ---------- writes ----------

    def save_visit(self, *, beneficiary_id: str, visit_type: str, lang: str, saved_at: str,
                   record: dict, transcript: list, receipt: list, flags: list[dict],
                   concerns: list[dict] = (), switches: list[dict] = (), session_key: str | None = None) -> int:
        with self._lock, self.db:
            cur = self.db.execute(
                "INSERT INTO visits (beneficiary_id, visit_type, lang, saved_at, record, transcript, receipt)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (beneficiary_id, visit_type, lang, saved_at,
                 self._seal(record), self._seal(transcript), self._seal(receipt)))
            visit_id = cur.lastrowid
            if session_key:
                self.db.execute(
                    "INSERT INTO visit_reports (visit_id, session_key) VALUES (?, ?) "
                    "ON CONFLICT(session_key) DO UPDATE SET visit_id=excluded.visit_id, filed_at=NULL",
                    (visit_id, session_key))
            self.db.executemany(
                "INSERT INTO audit (visit_id, at, kind, sign, flagged_by, quote) VALUES (?, ?, 'flag', ?, ?, ?)",
                [(visit_id, f["at"], f["sign"], f["by"], self._seal(f["quote"])) for f in flags])
            self.db.executemany(
                "INSERT INTO audit (visit_id, at, kind, flagged_by, quote) VALUES (?, ?, ?, 'asha', ?)",
                [(visit_id, c["at"], "concern_flagged" if c["flagged"] else "concern_noted", self._seal(c["quote"]))
                 for c in concerns])
            self.db.executemany(          # sign column holds "anc->hbnc"; nothing she said is in it
                "INSERT INTO audit (visit_id, at, kind, sign, flagged_by) VALUES (?, ?, 'visit_switch', ?, ?)",
                [(visit_id, w["at"], f"{w['from']}->{w['to']}", w["by"]) for w in switches])
            self.db.execute("INSERT INTO audit (visit_id, at, kind) VALUES (?, ?, 'saved')", (visit_id, saved_at))
        return visit_id

    def mark_undone(self, visit_id: int, at: str) -> None:
        """Her 'ruko' within 5 s: the row stays for the audit trail, but is no longer a saved visit."""
        with self._lock, self.db:
            self.db.execute("UPDATE visits SET status = 'undone' WHERE id = ?", (visit_id,))
            self.db.execute("INSERT INTO audit (visit_id, at, kind) VALUES (?, ?, 'undone')", (visit_id, at))

    def add_referral_step(self, flag_key: str, step: str, at: str) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO referrals (flag_key, step, at) VALUES (?, ?, ?)", (flag_key, step, at))

    def mark(self, item_key: str, kind: str, at: str) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT OR IGNORE INTO review_marks (item_key, kind, at) VALUES (?, ?, ?)",
                            (item_key, kind, at))

    # ---------- reads (ANM view, tests) ----------

    def referrals(self) -> dict[str, list[dict]]:
        """{flag_key: [{"step", "at"}, ...]} oldest first."""
        with self._lock:
            rows = self.db.execute("SELECT flag_key, step, at FROM referrals ORDER BY id").fetchall()
        out: dict[str, list[dict]] = {}
        for key, step, at in rows:
            out.setdefault(key, []).append({"step": step, "at": at})
        return out

    def marks(self) -> dict[str, dict]:
        with self._lock:
            rows = self.db.execute("SELECT item_key, kind, at FROM review_marks").fetchall()
        return {key: {"kind": kind, "at": at} for key, kind, at in rows}

    def load_visit(self, visit_id: int) -> dict | None:
        with self._lock:
            row = self.db.execute(
                "SELECT id, beneficiary_id, visit_type, lang, saved_at, status, record, transcript, receipt"
                " FROM visits WHERE id = ?", (visit_id,)).fetchone()
        if row is None:
            return None
        keys = ("id", "beneficiary_id", "visit_type", "lang", "saved_at", "status")
        return {**dict(zip(keys, row[:6])), "record": self._open(row[6]),
                "transcript": self._open(row[7]), "receipt": self._open(row[8])}

    def report_id(self, session_key: str) -> int | None:
        with self._lock:
            row = self.db.execute(
                "SELECT r.visit_id FROM visit_reports r JOIN visits v ON v.id=r.visit_id "
                "WHERE r.session_key=? AND v.status='saved'", (session_key,)).fetchone()
        return row[0] if row else None

    def file_report(self, visit_id: int, session_key: str, at: str) -> bool:
        with self._lock, self.db:
            cursor = self.db.execute(
                "UPDATE visit_reports SET filed_at=COALESCE(filed_at, ?) "
                "WHERE visit_id=? AND session_key=? AND EXISTS "
                "(SELECT 1 FROM visits WHERE id=? AND status='saved')",
                (at, visit_id, session_key, visit_id))
            return cursor.rowcount == 1

    def history(self, beneficiary_id: str) -> list[dict]:
        with self._lock:
            ids = self.db.execute(
                "SELECT v.id FROM visits v LEFT JOIN visit_reports r ON v.id=r.visit_id "
                "WHERE v.beneficiary_id=? AND v.status='saved' "
                "AND (r.visit_id IS NULL OR r.filed_at IS NOT NULL) ORDER BY v.id DESC",
                (beneficiary_id,)).fetchall()
        return [visit for (visit_id,) in ids
                if (visit := self.load_visit(visit_id)) and visit["status"] == "saved"]

    def previous_visit(self, visit: dict) -> dict | None:
        with self._lock:
            row = self.db.execute(
                "SELECT v.id FROM visits v LEFT JOIN visit_reports r ON v.id=r.visit_id "
                "WHERE v.beneficiary_id=? AND v.visit_type=? AND v.id<? AND v.status='saved' "
                "AND (r.visit_id IS NULL OR r.filed_at IS NOT NULL) ORDER BY v.id DESC LIMIT 1",
                (visit["beneficiary_id"], visit["visit_type"], visit["id"])).fetchone()
        baseline = self.load_visit(row[0]) if row else None
        return baseline if baseline and baseline["status"] == "saved" else None

    def audit(self, visit_id: int) -> list[dict]:
        with self._lock:
            rows = self.db.execute(
                "SELECT at, kind, sign, flagged_by, quote FROM audit WHERE visit_id = ? ORDER BY id",
                (visit_id,)).fetchall()
        return [{"at": at, "kind": kind, "sign": sign, "by": by, "quote": self._open(quote)}
                for at, kind, sign, by, quote in rows]

    def close(self) -> None:
        self.db.close()


def default_store() -> Store | None:
    """The app's store from .env (DB_KEY, optional DB_PATH). None, with a loud log, if DB_KEY is missing."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    key = os.getenv("DB_KEY", "").strip()
    if not key:
        log.error("DB_KEY is missing in .env: visits will NOT be saved")
        return None
    return Store(os.getenv("DB_PATH") or DEFAULT_DB, key)
