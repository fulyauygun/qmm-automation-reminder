"""Reminder decision logic (pure, fully unit-testable).

Rules
-----
* Milestones (default 30/15/7/1 days before the due date) fire once per
  document *and* due date. A revised document gets a new due date and
  therefore a fresh set of milestones.
* Catch-up: if the machine did not run on the exact milestone day, the
  next run sends only the most imminent missed milestone; the ones that
  were skipped are marked "superseded" so they are never sent late.
* After the due date has passed, an overdue notice is sent immediately and
  then repeated every ``overdue_repeat_days`` until the document is
  revised in the Excel file.
"""

from __future__ import annotations

from datetime import date

from .models import OVERDUE, Document, PlannedNotification, milestone_kind
from .state import StateStore


def plan_for_document(
    doc: Document,
    today: date,
    milestones_days: list[int],
    overdue_repeat_days: int,
    state: StateStore,
) -> PlannedNotification | None:
    days_left = (doc.due_date - today).days

    if days_left < 0:
        last = state.last_sent(doc.doc_id, doc.due_date, OVERDUE)
        if last is None or (today - last).days >= overdue_repeat_days:
            return PlannedNotification(doc, OVERDUE, days_left)
        return None

    applicable = sorted(m for m in milestones_days if days_left <= m)
    if not applicable:
        return None
    target = applicable[0]
    kind = milestone_kind(target)
    if state.was_handled(doc.doc_id, doc.due_date, kind):
        return None
    supersedes = tuple(milestone_kind(m) for m in applicable[1:])
    return PlannedNotification(doc, kind, days_left, supersedes)


def plan_run(
    documents: list[Document],
    today: date,
    milestones_days: list[int],
    overdue_repeat_days: int,
    state: StateStore,
) -> list[PlannedNotification]:
    planned = []
    for doc in documents:
        p = plan_for_document(doc, today, milestones_days, overdue_repeat_days, state)
        if p is not None:
            planned.append(p)
    # Most urgent first: overdue, then fewest days left.
    planned.sort(key=lambda p: p.days_left)
    return planned
