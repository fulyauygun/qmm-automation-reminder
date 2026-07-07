"""Notification channels.

Both notifiers implement the same two-method interface (``name``,
``send``); adding a future channel (e.g. a different chat system) means
adding one class here and one config block.
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage

import requests

from .config import EmailConfig, TeamsConfig
from .messages import facts_for, plain_text_for, summary_for, title_for
from .models import PlannedNotification

log = logging.getLogger(__name__)

_RETRIES = 3
_BACKOFF_SECONDS = (2, 4)
_TIMEOUT = 20


class NotificationError(Exception):
    pass


def _with_retries(action, describe: str):
    for attempt in range(_RETRIES):
        try:
            return action()
        except Exception as exc:  # noqa: BLE001 - report any transport error
            if attempt == _RETRIES - 1:
                raise NotificationError(f"{describe}: {exc}") from exc
            wait = _BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)]
            log.warning("%s failed (attempt %d): %s - retrying in %ss",
                        describe, attempt + 1, exc, wait)
            time.sleep(wait)


class TeamsWebhookNotifier:
    """Posts an Adaptive Card to a Teams channel via an incoming webhook
    created with Teams "Workflows" (Post to a channel when a webhook
    request is received). Data goes only to the company M365 tenant."""

    name = "teams"

    def __init__(self, cfg: TeamsConfig, ca_bundle: str | None = None):
        self._url = cfg.resolve_webhook_url()
        self._verify = ca_bundle if ca_bundle else True

    @property
    def recipient(self) -> str:
        return "teams-channel"

    def send(self, p: PlannedNotification) -> None:
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": self._card(p),
                }
            ],
        }

        def _post():
            resp = requests.post(
                self._url, json=payload, timeout=_TIMEOUT, verify=self._verify
            )
            if resp.status_code >= 300:
                raise RuntimeError(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )

        _with_retries(_post, f"Teams webhook ({p.document.title}, {p.kind})")

    def send_text(self, title: str, text: str) -> None:
        """Plain notice card - used to surface tool failures in the channel
        so a broken scheduled run never goes unnoticed."""
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "Bolder",
                                "color": "Attention",
                                "wrap": True,
                            },
                            {"type": "TextBlock", "text": text, "wrap": True},
                        ],
                    },
                }
            ],
        }

        def _post():
            resp = requests.post(
                self._url, json=payload, timeout=_TIMEOUT, verify=self._verify
            )
            if resp.status_code >= 300:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        _with_retries(_post, f"Teams webhook (notice: {title})")

    @staticmethod
    def _card(p: PlannedNotification) -> dict:
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "msteams": {"width": "Full"},
            "body": [
                {
                    "type": "TextBlock",
                    "text": title_for(p),
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Attention" if p.is_overdue else "Warning",
                    "wrap": True,
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": k, "value": v} for k, v in facts_for(p)
                    ],
                },
                {"type": "TextBlock", "text": summary_for(p), "wrap": True},
            ],
        }


class SmtpNotifier:
    """Plain SMTP mail via the internal relay. Credentials, if the relay
    requires them, come from environment variables - never from config."""

    name = "email"

    def __init__(self, cfg: EmailConfig, recipients: list[str] | None = None):
        self._cfg = cfg
        self._recipients = recipients if recipients is not None else cfg.recipients

    @property
    def recipient(self) -> str:
        return ", ".join(self._recipients)

    def send(self, p: PlannedNotification) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"{title_for(p)} – {p.document.title}"
        msg["From"] = self._cfg.from_address
        msg["To"] = ", ".join(self._recipients)
        msg.set_content(plain_text_for(p))

        def _send():
            with smtplib.SMTP(
                self._cfg.smtp_host, self._cfg.smtp_port, timeout=_TIMEOUT
            ) as smtp:
                if self._cfg.use_starttls:
                    smtp.starttls()
                user, password = self._cfg.resolve_credentials()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)

        _with_retries(_send, f"SMTP ({p.document.title}, {p.kind})")
