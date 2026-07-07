"""SQLite-backed send state (duplicate prevention).

``sent_reminders`` remembers which reminder was sent for which document
and due date, so a reminder is never sent twice. The due date is part of
the key: when a document is revised (new due date), all milestones are
automatically re-armed.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_reminders (
    doc_id   TEXT NOT NULL,
    due_date TEXT NOT NULL,
    kind     TEXT NOT NULL,
    status   TEXT NOT NULL,           -- 'sent' or 'superseded'
    sent_at  TEXT NOT NULL,           -- ISO timestamp
    PRIMARY KEY (doc_id, due_date, kind, sent_at)
);
"""


class StateStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- duplicate prevention -------------------------------------------

    def was_handled(self, doc_id: str, due_date: date, kind: str) -> bool:
        """True if this milestone was already sent or superseded."""
        cur = self._conn.execute(
            "SELECT 1 FROM sent_reminders WHERE doc_id=? AND due_date=? AND kind=?"
            " LIMIT 1",
            (doc_id, due_date.isoformat(), kind),
        )
        return cur.fetchone() is not None

    def last_sent(self, doc_id: str, due_date: date, kind: str) -> date | None:
        """Date of the most recent 'sent' record for this kind (for the
        repeating overdue notice)."""
        cur = self._conn.execute(
            "SELECT MAX(sent_at) FROM sent_reminders"
            " WHERE doc_id=? AND due_date=? AND kind=? AND status='sent'",
            (doc_id, due_date.isoformat(), kind),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        return datetime.fromisoformat(row[0]).date()

    def record_sent(
        self,
        doc_id: str,
        due_date: date,
        kind: str,
        superseded_kinds: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now()
        ts = now.isoformat(timespec="seconds")
        rows = [(doc_id, due_date.isoformat(), kind, "sent", ts)]
        rows += [
            (doc_id, due_date.isoformat(), k, "superseded", ts)
            for k in superseded_kinds
        ]
        self._conn.executemany(
            "INSERT OR IGNORE INTO sent_reminders"
            " (doc_id, due_date, kind, status, sent_at) VALUES (?,?,?,?,?)",
            rows,
        )
        self._conn.commit()
