"""Configuration loading and validation.

The YAML file contains no secrets. Secrets are resolved at runtime from
environment variables (or an ACL-protected file for the webhook URL).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class ExcelConfig:
    path: str
    sheet: str | None
    columns: dict[str, str]  # logical name -> header text
    id_columns: list[str]

    REQUIRED_COLUMNS = ("section", "revision_date", "due_date")


@dataclass
class ReminderConfig:
    milestones_days: list[int]
    overdue_repeat_days: int
    validity_years: int


@dataclass
class TeamsConfig:
    enabled: bool
    webhook_url_env: str
    webhook_url_file: str | None
    # @mention the people from the recipients sheet in every card, so they
    # get a personal Teams notification instead of only a channel post.
    mention_recipients: bool

    def resolve_webhook_url(self) -> str:
        url = os.environ.get(self.webhook_url_env, "").strip()
        if url:
            return url
        if self.webhook_url_file:
            p = Path(self.webhook_url_file)
            if p.is_file():
                url = p.read_text(encoding="utf-8").strip()
                if url:
                    return url
        raise ConfigError(
            "Teams webhook URL not found: set the environment variable "
            f"'{self.webhook_url_env}' (or configure notifications.teams."
            "webhook_url_file). The URL must never be hardcoded."
        )


@dataclass
class EmailConfig:
    enabled: bool
    smtp_host: str
    smtp_port: int
    use_starttls: bool
    username_env: str
    password_env: str
    from_address: str
    recipients: list[str]

    def resolve_credentials(self) -> tuple[str | None, str | None]:
        user = os.environ.get(self.username_env or "", "").strip() or None
        password = os.environ.get(self.password_env or "", "").strip() or None
        return user, password


@dataclass
class StorageConfig:
    state_db: Path
    log_dir: Path
    # Static HTML status page rewritten on every run; None disables it.
    report: Path | None


@dataclass
class Config:
    excel: ExcelConfig
    reminders: ReminderConfig
    teams: TeamsConfig
    email: EmailConfig
    # Worksheet in the control-list workbook that the QMM team maintains
    # themselves ("Ad" / "E-posta" / "Aktif" columns). Feeds Teams
    # mentions and, when enabled, the e-mail channel.
    recipients_sheet: str | None
    ca_bundle: str | None
    storage: StorageConfig
    base_dir: Path = field(default_factory=Path.cwd)


def _require(mapping: dict, key: str, context: str):
    if key not in mapping or mapping[key] in (None, ""):
        raise ConfigError(f"Missing required config value: {context}.{key}")
    return mapping[key]


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(
            f"Config file not found: {path}. "
            "Copy config.example.yaml to config.yaml and adjust it."
        )
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    base_dir = path.resolve().parent

    excel_raw = raw.get("excel") or {}
    columns = {
        k: str(v)
        for k, v in (excel_raw.get("columns") or {}).items()
        if v not in (None, "")
    }
    for logical in ExcelConfig.REQUIRED_COLUMNS:
        if logical not in columns:
            raise ConfigError(f"excel.columns.{logical} must be configured")
    id_columns = list(excel_raw.get("id_columns") or ["section", "approval_doc"])
    unknown = [c for c in id_columns if c not in columns]
    if unknown:
        raise ConfigError(
            f"excel.id_columns refers to unconfigured columns: {unknown}"
        )
    excel = ExcelConfig(
        path=str(_require(excel_raw, "path", "excel")),
        sheet=excel_raw.get("sheet") or None,
        columns=columns,
        id_columns=id_columns,
    )

    rem_raw = raw.get("reminders") or {}
    milestones = sorted({int(d) for d in rem_raw.get("milestones_days", [30, 15, 7, 1])})
    if not milestones or any(d < 0 for d in milestones):
        raise ConfigError("reminders.milestones_days must be non-negative integers")
    reminders = ReminderConfig(
        milestones_days=milestones,
        overdue_repeat_days=max(1, int(rem_raw.get("overdue_repeat_days", 7))),
        validity_years=int(rem_raw.get("validity_years", 3)),
    )

    notif_raw = raw.get("notifications") or {}
    teams_raw = notif_raw.get("teams") or {}
    teams = TeamsConfig(
        enabled=bool(teams_raw.get("enabled", False)),
        webhook_url_env=str(teams_raw.get("webhook_url_env", "QMM_TEAMS_WEBHOOK_URL")),
        webhook_url_file=teams_raw.get("webhook_url_file") or None,
        mention_recipients=bool(teams_raw.get("mention_recipients", True)),
    )
    email_raw = notif_raw.get("email") or {}
    email = EmailConfig(
        enabled=bool(email_raw.get("enabled", False)),
        smtp_host=str(email_raw.get("smtp_host", "")),
        smtp_port=int(email_raw.get("smtp_port", 25)),
        use_starttls=bool(email_raw.get("use_starttls", False)),
        username_env=str(email_raw.get("username_env", "")),
        password_env=str(email_raw.get("password_env", "")),
        from_address=str(email_raw.get("from_address", "")),
        recipients=[str(r) for r in (email_raw.get("recipients") or [])],
    )
    # Accept the sheet name at notifications level (current) or nested
    # under email (earlier layout).
    recipients_sheet = (
        notif_raw.get("recipients_sheet")
        or email_raw.get("recipients_sheet")
        or None
    )
    if email.enabled and not email.smtp_host:
        raise ConfigError("notifications.email is enabled but smtp_host missing")
    if email.enabled and not email.recipients and not recipients_sheet:
        raise ConfigError(
            "notifications.email is enabled but neither recipients nor"
            " notifications.recipients_sheet is configured"
        )
    if not teams.enabled and not email.enabled:
        raise ConfigError("At least one notification channel must be enabled")

    storage_raw = raw.get("storage") or {}

    def _resolve(p: str) -> Path:
        candidate = Path(p)
        return candidate if candidate.is_absolute() else base_dir / candidate

    report_raw = storage_raw.get("report", "rapor/index.html")
    storage = StorageConfig(
        state_db=_resolve(str(storage_raw.get("state_db", "state/qmm_reminder.db"))),
        log_dir=_resolve(str(storage_raw.get("log_dir", "logs"))),
        report=_resolve(str(report_raw)) if report_raw else None,
    )

    return Config(
        excel=excel,
        reminders=reminders,
        teams=teams,
        email=email,
        recipients_sheet=recipients_sheet,
        ca_bundle=notif_raw.get("ca_bundle") or None,
        storage=storage,
        base_dir=base_dir,
    )
