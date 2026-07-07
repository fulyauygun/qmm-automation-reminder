from datetime import date, datetime
from pathlib import Path

from qmm_reminder.state import StateStore

DUE = date(2026, 8, 1)


def test_was_handled_covers_sent_and_superseded(tmp_path: Path):
    with StateStore(tmp_path / "s.db") as s:
        assert not s.was_handled("d1", DUE, "T-7")
        s.record_sent("d1", DUE, "T-7", superseded_kinds=("T-15", "T-30"))
        assert s.was_handled("d1", DUE, "T-7")
        assert s.was_handled("d1", DUE, "T-15")
        assert s.was_handled("d1", DUE, "T-30")
        assert not s.was_handled("d1", DUE, "T-1")
        # different due date = different key
        assert not s.was_handled("d1", date(2029, 8, 1), "T-7")


def test_last_sent_ignores_superseded(tmp_path: Path):
    with StateStore(tmp_path / "s.db") as s:
        assert s.last_sent("d1", DUE, "OVERDUE") is None
        s.record_sent("d1", DUE, "OVERDUE", now=datetime(2026, 8, 2, 8, 0))
        s.record_sent("d1", DUE, "OVERDUE", now=datetime(2026, 8, 9, 8, 0))
        assert s.last_sent("d1", DUE, "OVERDUE") == date(2026, 8, 9)


def test_audit_rows_written(tmp_path: Path):
    db = tmp_path / "s.db"
    with StateStore(db) as s:
        s.audit("run1", doc_id="d1", title="QMM-TL-001", section="Üretim",
                due_date="2026-08-01", kind="T-7", channel="teams",
                recipient="teams-channel", status="SENT")
        cur = s._conn.execute("SELECT run_id, status, channel FROM audit_log")
        assert cur.fetchall() == [("run1", "SENT", "teams")]
