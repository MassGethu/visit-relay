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
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL REFERENCES visits(id),
    at TEXT NOT NULL,
    kind TEXT NOT NULL,              -- 'flag' | 'concern_noted' | 'concern_flagged' | 'saved' | 'undone'
    sign TEXT,
    flagged_by TEXT,                             -- 'rules' | 'llm' | 'asha' (worker concern)
    quote BLOB
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
                   concerns: list[dict] = ()) -> int:
        with self._lock, self.db:
            cur = self.db.execute(
                "INSERT INTO visits (beneficiary_id, visit_type, lang, saved_at, record, transcript, receipt)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (beneficiary_id, visit_type, lang, saved_at,
                 self._seal(record), self._seal(transcript), self._seal(receipt)))
            visit_id = cur.lastrowid
            self.db.executemany(
                "INSERT INTO audit (visit_id, at, kind, sign, flagged_by, quote) VALUES (?, ?, 'flag', ?, ?, ?)",
                [(visit_id, f["at"], f["sign"], f["by"], self._seal(f["quote"])) for f in flags])
            self.db.executemany(
                "INSERT INTO audit (visit_id, at, kind, flagged_by, quote) VALUES (?, ?, ?, 'asha', ?)",
                [(visit_id, c["at"], "concern_flagged" if c["flagged"] else "concern_noted", self._seal(c["quote"]))
                 for c in concerns])
            self.db.execute("INSERT INTO audit (visit_id, at, kind) VALUES (?, ?, 'saved')", (visit_id, saved_at))
        return visit_id

    def mark_undone(self, visit_id: int, at: str) -> None:
        """Her 'ruko' within 5 s: the row stays for the audit trail, but is no longer a saved visit."""
        with self._lock, self.db:
            self.db.execute("UPDATE visits SET status = 'undone' WHERE id = ?", (visit_id,))
            self.db.execute("INSERT INTO audit (visit_id, at, kind) VALUES (?, ?, 'undone')", (visit_id, at))

    # ---------- reads (ANM view, tests) ----------

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
