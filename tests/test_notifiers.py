from datetime import date

import pytest

from qmm_reminder.config import TeamsConfig
from qmm_reminder.models import Document, PlannedNotification
from qmm_reminder.notifiers import TeamsWebhookNotifier


@pytest.fixture()
def notifier(monkeypatch):
    def build(mentions):
        monkeypatch.setenv("TEST_WEBHOOK", "https://example.com/hook")
        cfg = TeamsConfig(
            enabled=True, webhook_url_env="TEST_WEBHOOK",
            webhook_url_file=None, mention_recipients=True,
        )
        return TeamsWebhookNotifier(cfg, mentions=mentions)
    return build


def planned() -> PlannedNotification:
    d = Document(
        doc_id="d1", title="QMM-TL-001", section="Üretim", revision_no="01",
        prepared_by="A. Yılmaz", revision_date=None,
        due_date=date(2026, 8, 1), source_row=2,
    )
    return PlannedNotification(d, "T-7", 7)


def test_card_mentions_people(notifier):
    n = notifier([("Çağlar Yılmaz", "caglar@example.com"),
                  ("Ulvi Demir", "ulvi@example.com")])
    card = n._card(planned())
    entities = card["msteams"]["entities"]
    assert [e["mentioned"]["id"] for e in entities] == [
        "caglar@example.com", "ulvi@example.com"
    ]
    mention_text = card["body"][-1]["text"]
    assert "<at>Çağlar Yılmaz</at>" in mention_text
    assert "<at>Ulvi Demir</at>" in mention_text
    assert n.recipient == "teams-channel + caglar@example.com, ulvi@example.com"


def test_card_without_mentions_has_no_entities(notifier):
    card = notifier([])._card(planned())
    assert "entities" not in card["msteams"]
    assert all("<at>" not in str(block) for block in card["body"])
