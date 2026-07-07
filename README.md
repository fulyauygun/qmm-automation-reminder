# QMM Working Instruction Reminder

Automated expiry reminders for the **QMM Working Instructions Control
List** (Excel). Working instructions are valid for 3 years; this tool
reads the control list from the network share once a day and posts a
Turkish reminder card to a Microsoft Teams channel **30 / 15 / 7 / 1 days
before** a document's validity expires, and **repeatedly after** expiry
until the document is revised.

Everything runs locally on a Windows PC inside the company network. The
Excel file is opened read-only in place — it is never copied, uploaded or
sent to any external service. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technology
decision record and security design.

## How it works

```
Task Scheduler (daily) ─► run_qmm_reminder.bat ─► py -3 -m qmm_reminder
    reads Excel (read-only, network share)
    decides which reminders are due today          (engine.py)
    posts Adaptive Cards to Teams webhook          (notifiers.py)
    records state + audit trail in local SQLite    (state.py)
    writes rotating log files                      (logs/)
```

Key behaviors:

* **No duplicates** — each milestone fires once per document *and* due
  date. When a document is revised (new due date in the Excel), all
  milestones re-arm automatically.
* **Catch-up safe** — if the PC was off on the exact milestone day, the
  next run sends only the most imminent missed reminder, never a burst.
* **Overdue** — after expiry, a red overdue card repeats every 7 days
  (configurable) until the row is updated.
* **Audit trail** — every notification attempt (SENT / FAILED / DRY-RUN)
  is stored in `state/qmm_reminder.db`, table `audit_log`.
* **Data minimization** — the `Revizyon İçeriği` column is never read or
  transmitted.

## Installation (Windows office PC)

Prerequisite: Python 3.10+ from the company software center
(python.org installer with "py launcher" is fine).

```bat
cd C:\QMM\qmm-automation-reminder
py -3 -m pip install -r requirements.txt
copy config.example.yaml config.yaml
notepad config.yaml          :: set the UNC path to the Excel file
```

### Teams webhook (the only secret)

1. In the target Teams channel: **⋯ → Workflows → "Post to a channel when
   a webhook request is received"** → copy the webhook URL.
2. Store it as a *user* environment variable — never in a file inside
   this folder and never in git:

```bat
setx QMM_TEAMS_WEBHOOK_URL "https://prod-...logic.azure.com/workflows/..."
```

(Alternative: put the URL alone in a file readable only by the service
user and set `notifications.teams.webhook_url_file` in `config.yaml`.)

### Test before scheduling

```bat
py -3 -m qmm_reminder --config config.yaml --dry-run
```

`--dry-run` logs exactly what would be sent, sends nothing and changes no
state. Repeat until the output matches your expectation, then send once
for real: `py -3 -m qmm_reminder --config config.yaml`.

### Schedule the daily run

```bat
schtasks /Create /TN "QMM Reminder" /SC DAILY /ST 08:00 ^
  /TR "C:\QMM\qmm-automation-reminder\run_qmm_reminder.bat"
```

In Task Scheduler, enable *"Run task as soon as possible after a
scheduled start is missed"* so a late PC start still triggers the run.

## Configuration

All settings live in `config.yaml` (git-ignored; see the commented
`config.example.yaml`): Excel path and column headers, milestone days,
overdue repeat interval, notification channels. An SMTP e-mail channel is
included but disabled by default — set `notifications.email.enabled: true`
and the process leader's address under `recipients` to also send e-mails
via the internal relay.

## Operations

* **Logs:** `logs/qmm_reminder.log` (rotating, UTF-8).
* **Audit queries:** e.g. everything sent last month:
  `SELECT ts, title, kind, channel, status FROM audit_log` in
  `state/qmm_reminder.db` (any SQLite viewer).
* **Exit codes:** `0` success · `1` at least one send failed (retried
  automatically next run) · `2` configuration or Excel read error.
* **Rows the tool cannot interpret** (missing dates) are skipped, logged
  as warnings and written to the audit log — check the log after editing
  the Excel structure.

## Development

```bat
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest tests\
py -3 tools\create_sample_excel.py     :: fictitious demo data
```

## Kısa Türkçe özet

Bu araç, QMM çalışma talimatları kontrol listesini her gün ağ
paylaşımından okur; geçerlilik süresinin dolmasına 30 / 15 / 7 / 1 gün
kala ve süre dolduktan sonra 7 günde bir, ilgili Teams kanalına Türkçe
hatırlatma kartı gönderir. Dosya hiçbir dış sisteme yüklenmez; webhook
adresi ortam değişkeninde saklanır; gönderilen her bildirim denetim
kaydına (audit log) işlenir. Kurulum ve zamanlama adımları yukarıdadır.
