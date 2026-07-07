"""Command-line entry point.

Typical scheduled invocation (Windows Task Scheduler, daily):

    py -3 -m qmm_reminder --config C:\\QMM\\reminder\\config.yaml

Options:
    --dry-run   evaluate and log what would be sent, send nothing,
                change no state (safe to run any time)
    --today     override "today" for testing, format YYYY-MM-DD
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import __version__
from .config import Config, ConfigError, load_config
from .engine import plan_run
from .excel_reader import ExcelReadError, read_documents, read_recipients
from .notifiers import NotificationError, SmtpNotifier, TeamsWebhookNotifier
from .report import write_report
from .state import StateStore

log = logging.getLogger("qmm_reminder")


def _setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(
        log_dir / "qmm_reminder.log",
        maxBytes=1_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console)


def _sheet_recipients(cfg: Config) -> list[tuple[str, str]]:
    """(name, e-mail) pairs from the team-maintained Excel sheet."""
    if not cfg.recipients_sheet:
        return []
    people, warnings = read_recipients(Path(cfg.excel.path), cfg.recipients_sheet)
    for w in warnings:
        log.warning("%s", w)
    return people


def _build_notifiers(cfg: Config) -> list:
    people = _sheet_recipients(cfg)
    notifiers = []
    if cfg.teams.enabled:
        mentions = people if cfg.teams.mention_recipients else []
        if mentions:
            log.info("Teams cards will mention %d person(s)", len(mentions))
        notifiers.append(TeamsWebhookNotifier(cfg.teams, cfg.ca_bundle, mentions))
    if cfg.email.enabled:
        recipients = list(cfg.email.recipients)
        seen = {r.casefold() for r in recipients}
        recipients += [e for _, e in people if e.casefold() not in seen]
        if recipients:
            log.info("E-mail recipients: %d address(es)", len(recipients))
            notifiers.append(SmtpNotifier(cfg.email, recipients))
        else:
            log.error(
                "E-mail channel enabled but no recipients found (config list"
                " empty and sheet %r yielded none) - e-mail sending skipped",
                cfg.recipients_sheet,
            )
    return notifiers


def run(cfg: Config, today: date, dry_run: bool) -> int:
    run_id = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    log.info("Run %s starting (version %s, today=%s, dry_run=%s)",
             run_id, __version__, today, dry_run)

    documents, warnings = read_documents(cfg.excel, cfg.reminders.validity_years)
    for w in warnings:
        log.warning("Excel: %s", w)
    log.info("Read %d document(s) from %s", len(documents), cfg.excel.path)

    if cfg.storage.report:
        try:
            write_report(cfg.storage.report, documents, today,
                         Path(cfg.excel.path).name)
            log.info("Status page written: %s", cfg.storage.report)
        except OSError as exc:
            # A broken status page must never block the reminders.
            log.warning("Status page could not be written: %s", exc)

    with StateStore(cfg.storage.state_db) as state:
        planned = plan_run(
            documents,
            today,
            cfg.reminders.milestones_days,
            cfg.reminders.overdue_repeat_days,
            state,
        )
        log.info("%d notification(s) due", len(planned))

        if dry_run:
            for p in planned:
                log.info("[DRY-RUN] would send %s for '%s' (Bölüm: %s, due %s)",
                         p.kind, p.document.title, p.document.section,
                         p.document.due_date)
            log.info("Run %s finished (dry run)", run_id)
            return 0

        notifiers = _build_notifiers(cfg)
        failures = 0
        for p in planned:
            all_ok = True
            for notifier in notifiers:
                try:
                    notifier.send(p)
                except NotificationError as exc:
                    all_ok = False
                    failures += 1
                    log.error("Send failed: %s", exc)
            # Mark as sent only when every enabled channel succeeded, so a
            # failed channel is retried on the next run. A missed reminder
            # is a compliance risk; a repeated one is only noise.
            if all_ok:
                state.record_sent(
                    p.document.doc_id, p.document.due_date, p.kind, p.supersedes
                )
                log.info("Sent %s for '%s' (Bölüm: %s, due %s)",
                         p.kind, p.document.title, p.document.section,
                         p.document.due_date)

    if failures:
        log.error("Run %s finished with %d failure(s)", run_id, failures)
        return 1
    log.info("Run %s finished successfully", run_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qmm_reminder",
        description="QMM working-instruction expiry reminder",
    )
    parser.add_argument("--config", default="config.yaml",
                        help="path to config.yaml (default: ./config.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="log what would be sent; send nothing")
    parser.add_argument("--today", metavar="YYYY-MM-DD",
                        help="override today's date (testing only)")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    _setup_logging(cfg.storage.log_dir)

    today = date.fromisoformat(args.today) if args.today else date.today()
    try:
        return run(cfg, today, args.dry_run)
    except (ConfigError, ExcelReadError) as exc:
        log.error("%s", exc)
        _report_failure(cfg, str(exc), dry_run=args.dry_run)
        return 2
    except Exception as exc:
        log.exception("Unexpected error")
        _report_failure(cfg, f"{type(exc).__name__}: {exc}", dry_run=args.dry_run)
        return 2


def _report_failure(cfg: Config, message: str, dry_run: bool) -> None:
    """Best effort: surface a broken run in the Teams channel so the team
    notices even when nobody reads the log files. Never raises."""
    if dry_run or not cfg.teams.enabled:
        return
    try:
        mentions = []
        if cfg.teams.mention_recipients:
            try:
                mentions = _sheet_recipients(cfg)
            except Exception:  # noqa: BLE001 - Excel may be the broken part
                mentions = []
        TeamsWebhookNotifier(cfg.teams, cfg.ca_bundle, mentions).send_text(
            "🔴 QMM hatırlatma otomasyonu ÇALIŞAMADI",
            "Bugünkü kontrol tamamlanamadı, hatırlatmalar gönderilemedi. "
            f"Hata: {message} — Lütfen log dosyasını kontrol edin "
            "(kurulum klasörü altında logs\\qmm_reminder.log).",
        )
    except Exception as exc:  # noqa: BLE001 - reporting must never crash
        log.error("Failure notice could not be sent to Teams: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
