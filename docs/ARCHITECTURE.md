# QMM Reminder — Architecture & Technology Decision Record

Status: accepted · Date: 2026-07-07 · Scope: version 1

## 1. Business problem

The QMM department maintains a controlled Excel list ("QMM Working
Instructions Control List") of 10–20 working instructions. Each
instruction is valid for 3 years after its last revision. The process
leader must be reminded **30 / 15 / 7 / 1 days before** the validity
expires and **repeatedly after** it has expired, until the document is
revised. Notifications go to a Microsoft Teams channel; texts are Turkish.

Non-functional requirements:

* **Confidentiality** — the list contains quality-management information.
  It must not be uploaded to external platforms or third-party AI services.
* **On-premise execution** — runs on a Windows office PC inside the
  company network; the Excel file stays on the internal network share.
* **No hardcoded secrets** — webhook URL / SMTP credentials come from the
  environment, never from code or committed config.
* **Traceability** — runs, sends and failures are written to a rotating
  log file. (A structured audit-log table was considered and dropped from
  scope by QMM decision on 2026-07-07; it can be reinstated later.)
* **No duplicates** — each milestone fires exactly once per document
  revision cycle.
* **Successor-proof** — the intern who builds it will leave; the tool must
  be boring, documented and testable.

## 2. Technology options considered

| Option | Security | Maintainability | Scalability | Deployment | Enterprise fit | Long-term |
|---|---|---|---|---|---|---|
| **Python + Task Scheduler** ✅ | All processing local; only outbound call is to the company M365 tenant (Teams webhook). Secrets via env vars. | Plain code, unit tests, config/logic separation. Python is a supported standard tool in most industrial IT catalogs. | Handles thousands of rows; notifier interface is pluggable. | One Python install + one scheduled task. No server, no license. | High — no admin consent, no cloud connectors. | Code survives personnel changes; migration path to server/DB is trivial. |
| Power Automate | Data stays in the corporate tenant, **but** the flow itself processes the file in the cloud service, and reading a *network-share* file requires an on-premises data gateway (IT project) or moving the file to SharePoint. | Low-code flows degrade into unmaintainable diagrams; tied to the creating user's account — breaks when that account is disabled. | Limited by connector quotas. | Premium connector licensing questions. | Depends on tenant governance policy. | Fragile ownership model. |
| Excel VBA | Macro-enabled workbooks are commonly blocked/flagged by industrial security policy; credentials historically end up in the macro. | Code trapped inside the very document it monitors; breaks when the file is open/locked by a user; no version control, no tests. | Poor. | "Deployment" = editing the production document. | Low. | Poor. |
| Outlook COM automation | Local, but COM automation from a scheduled task is fragile (profile/session issues) and programmatic send triggers security prompts. | Poor. | Poor. | Brittle. | Low. | Poor. Also: the chosen channel is Teams, not mail. |
| Internal web application | Good, but requires a server, hosting approval, authentication integration — an IT project. | Good. | Good. | Heavy. | Good but slow to obtain. | Good — this is the *future* shape, not V1. |
| Database-based solution | Good. | Good. | Good. | Requires migrating the master list out of Excel — but the Excel **is** the controlled QM document today; duplicating it creates a second source of truth and a data-consistency risk. | — | Future phase, together with a web UI. |

**Decision:** Python 3 (openpyxl, requests, PyYAML — three vetted
libraries) scheduled by Windows Task Scheduler; Microsoft Teams
incoming-webhook (Workflows) notifications; SQLite for send-state
(duplicate prevention). SQLite is *not* a migration of the document
list — it stores only what the tool itself generates.

## 3. Architecture

```
Windows Task Scheduler (daily, e.g. 08:00)
        │
        ▼
run_qmm_reminder.bat ──► py -3 -m qmm_reminder --config config.yaml
        │
        ├── config.py        loads config.yaml (no secrets inside)
        ├── excel_reader.py  opens the .xlsx READ-ONLY on the network share
        ├── engine.py        pure date logic: which reminder is due today?
        ├── state.py         SQLite: sent_reminders (duplicate prevention)
        ├── notifiers.py     TeamsWebhookNotifier / SmtpNotifier (pluggable)
        ├── report.py        static HTML status page (rapor/index.html,
        │                    stays on the internal share - never hosted
        │                    externally)
        └── logs/            rotating qmm_reminder.log
        
Outbound traffic: exactly one HTTPS POST per notification,
to the company's own M365 tenant (Teams webhook URL).
```

### Reminder semantics

* Milestone key = `(document identity, due date, milestone)`. The due date
  in the key means a **revised document automatically re-arms all
  milestones** — no manual reset.
* **Catch-up:** the PC may be off on the exact milestone day. Rule: fire
  the *most imminent* milestone whose window has been entered and not yet
  handled; mark skipped larger ones `superseded` (never sent late, never
  sent as a burst of four).
* **Overdue:** first notice on the first run after expiry, then repeated
  every `overdue_repeat_days` (default 7) until the row is revised.
* **Failure handling:** a milestone is marked sent only when every enabled
  channel succeeded; otherwise the next daily run retries. A missed
  reminder is a compliance risk; a repeated one is only noise.

### Security measures

| Requirement | Implementation |
|---|---|
| No external upload | File read in place from the share; only notification metadata leaves the machine, and only to the corporate tenant |
| Data minimization | `Revizyon İçeriği` (change description) is never read or sent |
| No hardcoded secrets | Webhook URL from env var `QMM_TEAMS_WEBHOOK_URL` (or an NTFS-protected file); SMTP credentials from env vars; `config.yaml` is git-ignored |
| Access control | Delegated to existing NTFS/AD rights on the share; the tool needs read-only access; install folder restricted to the service user |
| Traceability | Rotating text log (`logs/qmm_reminder.log`): every run, send and failure with timestamps |
| TLS | `verify` on by default; corporate CA bundle configurable (`ca_bundle`) |

## 4. Future phases (explicitly out of scope for V1)

1. **Per-section routing** — map `Bölüm` → separate Teams channel or
   leader e-mail once the recipient list is confirmed.
2. **SharePoint integration** — move the list to SharePoint; read via
   Graph; enables Power BI without touching this tool's engine.
3. **Structured audit trail** — reinstate a notification audit table in
   the SQLite store (dropped from V1 scope) if QM audits later require a
   queryable record; the log file covers traceability until then.
4. **Power BI dashboard** — compliance dashboard (reminders sent vs.
   overdue days); easiest after the audit trail returns.
5. **Escalation ladder** — second overdue notice to the department head.
6. **Database migration + web interface** — when the list outgrows Excel,
   replace `excel_reader.py` with a DB reader; engine and notifiers are
   unchanged by design.
7. **Approval workflow / document version tracking** — full eQMS
   territory; evaluate commercial systems before building.
8. **SAP integration** — pull document master data from SAP DMS instead
   of Excel.
