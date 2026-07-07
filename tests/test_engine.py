from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from qmm_reminder.engine import plan_for_document, plan_run
from qmm_reminder.models import OVERDUE, Document
from qmm_reminder.state import StateStore

MILESTONES = [30, 15, 7, 1]
OVERDUE_REPEAT = 7
TODAY = date(2026, 7, 7)


@pytest.fixture()
def state(tmp_path: Path):
    with StateStore(tmp_path / "state.db") as s:
        yield s


def doc(due: date, doc_id: str = "doc1") -> Document:
    return Document(
        doc_id=doc_id,
        title="QMM-TL-001",
        section="Üretim",
        revision_no="02",
        prepared_by="A. Yılmaz",
        revision_date=due.replace(year=due.year - 3),
        due_date=due,
        source_row=2,
    )


def plan(d: Document, today: date, state: StateStore):
    return plan_for_document(d, today, MILESTONES, OVERDUE_REPEAT, state)


def test_no_reminder_far_from_due(state):
    assert plan(doc(TODAY + timedelta(days=45)), TODAY, state) is None


def test_exact_milestone_day(state):
    p = plan(doc(TODAY + timedelta(days=30)), TODAY, state)
    assert p is not None
    assert p.kind == "T-30"
    assert p.days_left == 30
    assert p.supersedes == ()


def test_between_milestones_fires_most_imminent(state):
    p = plan(doc(TODAY + timedelta(days=20)), TODAY, state)
    assert p.kind == "T-30"  # 20 <= 30, most imminent applicable is 30


def test_catch_up_sends_only_one_and_supersedes_missed(state):
    # First ever run happens 5 days before due: only T-7 goes out,
    # T-15 and T-30 are superseded, T-1 stays armed.
    p = plan(doc(TODAY + timedelta(days=5)), TODAY, state)
    assert p.kind == "T-7"
    assert p.supersedes == ("T-15", "T-30")
    state.record_sent(p.document.doc_id, p.document.due_date, p.kind, p.supersedes)

    assert plan(doc(TODAY + timedelta(days=5)), TODAY, state) is None
    later = plan(doc(TODAY + timedelta(days=5)), TODAY + timedelta(days=4), state)
    assert later.kind == "T-1"


def test_duplicate_prevention_same_day_rerun(state):
    d = doc(TODAY + timedelta(days=7))
    p = plan(d, TODAY, state)
    assert p.kind == "T-7"
    state.record_sent(d.doc_id, d.due_date, p.kind, p.supersedes)
    assert plan(d, TODAY, state) is None


def test_revision_re_arms_milestones(state):
    d = doc(TODAY + timedelta(days=7))
    p = plan(d, TODAY, state)
    state.record_sent(d.doc_id, d.due_date, p.kind, p.supersedes)
    # Document revised: same doc_id, new due date -> milestones fire again.
    revised = doc(TODAY + timedelta(days=7 + 365))
    assert plan(revised, TODAY + timedelta(days=365), state).kind == "T-7"


def test_due_today_uses_t1_kind(state):
    p = plan(doc(TODAY), TODAY, state)
    assert p.kind == "T-1"
    assert p.days_left == 0


def test_overdue_first_and_repeat_interval(state):
    d = doc(TODAY - timedelta(days=3))
    p = plan(d, TODAY, state)
    assert p.kind == OVERDUE
    assert p.days_left == -3
    state.record_sent(d.doc_id, d.due_date, OVERDUE,
                      now=datetime(2026, 7, 7, 8, 0))

    # Next day: within repeat interval -> silent.
    assert plan(d, TODAY + timedelta(days=1), state) is None
    # After the interval: repeats.
    again = plan(d, TODAY + timedelta(days=OVERDUE_REPEAT), state)
    assert again is not None and again.kind == OVERDUE


def test_plan_run_orders_most_urgent_first(state):
    docs = [
        doc(TODAY + timedelta(days=7), doc_id="a"),
        doc(TODAY - timedelta(days=2), doc_id="b"),
        doc(TODAY + timedelta(days=1), doc_id="c"),
    ]
    kinds = [p.kind for p in plan_run(docs, TODAY, MILESTONES, OVERDUE_REPEAT, state)]
    assert kinds == [OVERDUE, "T-1", "T-7"]
