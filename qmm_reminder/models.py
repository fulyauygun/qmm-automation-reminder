"""Core data types shared by the reader, engine and notifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

OVERDUE = "OVERDUE"


def milestone_kind(days: int) -> str:
    return f"T-{days}"


@dataclass(frozen=True)
class Document:
    """One row of the control list, reduced to what the reminder needs.

    ``Revizyon İçeriği`` is intentionally not read: it may contain
    confidential change descriptions and is not needed for reminding.
    """

    doc_id: str
    title: str
    section: str
    revision_no: str
    prepared_by: str
    revision_date: date | None
    due_date: date
    source_row: int


@dataclass(frozen=True)
class PlannedNotification:
    """A notification the engine decided to send in this run."""

    document: Document
    kind: str  # "T-30", "T-15", "T-7", "T-1" or "OVERDUE"
    days_left: int  # negative when overdue
    # Milestones skipped because the run happened after they had passed
    # (e.g. machine was off). They are recorded as superseded so they are
    # never sent late on a later run.
    supersedes: tuple[str, ...] = field(default=())

    @property
    def is_overdue(self) -> bool:
        return self.kind == OVERDUE
