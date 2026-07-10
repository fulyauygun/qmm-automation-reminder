"""QMM Talimat gecerlilik tarihi hatirlatma scripti.

data/QMM_Talimat_Index.xlsx dosyasindaki "Liste" sayfasini okur, her talimatin
son gecerlilik tarihine (H sutunu) kalan gun sayisini hesaplar. Kalan gun
30 / 15 / 7 / 1 esiklerinden birine denk geliyorsa config/recipients.json
icindeki alicilara ozet bir hatirlatma maili gonderir.

Ayni (talimat, esik) kombinasyonu icin tekrar mail atilmamasi icin gonderilen
hatirlatmalar scripts/state/sent_reminders.json dosyasina kaydedilir.
"""

import argparse
import json
import os
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = ROOT / "data" / "QMM_Talimat_Index.xlsx"
RECIPIENTS_PATH = ROOT / "config" / "recipients.json"
STATE_PATH = ROOT / "scripts" / "state" / "sent_reminders.json"
SHEET_NAME = "Liste"
REMINDER_THRESHOLDS = [30, 15, 7, 1]

# Liste sayfasindaki sutun indeksleri (1-indexli, openpyxl ile uyumlu)
COL_TALIMAT = 2
COL_BOLUM = 3
COL_REVIZYON_NO = 4
COL_REVIZYON_TARIHI = 5
COL_HAZIRLAYAN = 6
COL_SON_GECERLILIK = 8
DATA_START_ROW = 3


def load_documents(excel_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb[SHEET_NAME]

    documents = []
    for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
        talimat = row[COL_TALIMAT - 1]
        expiry = row[COL_SON_GECERLILIK - 1]
        if not talimat or not isinstance(expiry, datetime):
            continue
        documents.append(
            {
                "talimat": str(talimat).strip(),
                "bolum": row[COL_BOLUM - 1],
                "revizyon_no": row[COL_REVIZYON_NO - 1],
                "revizyon_tarihi": row[COL_REVIZYON_TARIHI - 1],
                "hazirlayan": row[COL_HAZIRLAYAN - 1],
                "son_gecerlilik": expiry.date(),
            }
        )
    return documents


def load_recipients(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("recipients", [])


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return set(json.load(f))


def save_state(path: Path, state: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, ensure_ascii=False, indent=2)


def find_due_reminders(documents: list[dict], today: date, sent: set[str]) -> list[dict]:
    due = []
    for doc in documents:
        days_left = (doc["son_gecerlilik"] - today).days
        if days_left not in REMINDER_THRESHOLDS:
            continue
        key = f"{doc['talimat']}|{doc['son_gecerlilik'].isoformat()}|{days_left}"
        if key in sent:
            continue
        due.append({**doc, "days_left": days_left, "state_key": key})
    return due


# Kalan gune gore satirin vurgu rengi (kirmiziya yaklastikca aciliyet artar)
URGENCY_COLORS = {
    1: "#dc2626",   # kirmizi
    7: "#f97316",   # turuncu
    15: "#eab308",  # sari
    30: "#2563eb",  # mavi
}


def build_subject(due_items: list[dict], today: date) -> str:
    base = f"QMM Talimat Geçerlilik Tarihi Hatırlatma - {today.strftime('%d.%m.%Y')} ({len(due_items)} talimat)"
    if any(item["days_left"] == 1 for item in due_items):
        urgent_count = sum(1 for item in due_items if item["days_left"] == 1)
        return f"⚠️ ACİL: {urgent_count} talimatın süresi yarın doluyor - {base}"
    return base


def build_email_text(due_items: list[dict], today: date) -> str:
    lines = [
        "Merhaba,",
        "",
        f"{today.strftime('%d.%m.%Y')} tarihi itibariyle aşağıdaki QMM çalışma "
        "talimatlarının geçerlilik süresi doluyor. Değişiklik olmaması durumunda "
        "belirtilen tarihe kadar revize edilmesi gerekiyor:",
        "",
    ]
    due_items_sorted = sorted(due_items, key=lambda d: d["days_left"])
    for item in due_items_sorted:
        lines.append(
            f"- [{item['days_left']} gün kaldı] {item['talimat']} "
            f"(Bölüm: {item['bolum']}, Son geçerlilik: "
            f"{item['son_gecerlilik'].strftime('%d.%m.%Y')})"
        )
    lines += [
        "",
        "Bu mail QMM Talimat Hatırlatma otomasyonu tarafından otomatik olarak "
        "gönderilmiştir.",
    ]
    return "\n".join(lines)


def build_email_html(due_items: list[dict], today: date) -> str:
    due_items_sorted = sorted(due_items, key=lambda d: d["days_left"])
    rows = []
    for item in due_items_sorted:
        color = URGENCY_COLORS.get(item["days_left"], "#2563eb")
        rows.append(
            f"""
            <tr>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{item['talimat']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{item['bolum']}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{item['son_gecerlilik'].strftime('%d.%m.%Y')}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                <span style="display:inline-block;padding:3px 10px;border-radius:12px;background:{color};color:#ffffff;font-weight:bold;font-size:13px;">
                  {item['days_left']} gün kaldı
                </span>
              </td>
            </tr>"""
        )

    return f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;color:#111827;">
        <p>Merhaba,</p>
        <p>
          {today.strftime('%d.%m.%Y')} tarihi itibariyle aşağıdaki QMM çalışma talimatlarının
          geçerlilik süresi doluyor. Değişiklik olmaması durumunda belirtilen tarihe kadar
          revize edilmesi gerekiyor:
        </p>
        <table style="border-collapse:collapse;width:100%;max-width:720px;border:1px solid #e5e7eb;">
          <thead>
            <tr style="background:#f3f4f6;text-align:left;">
              <th style="padding:10px 12px;">Talimat Adı</th>
              <th style="padding:10px 12px;">Bölüm</th>
              <th style="padding:10px 12px;">Son Geçerlilik Tarihi</th>
              <th style="padding:10px 12px;">Kalan Gün</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        <p style="color:#6b7280;font-size:13px;margin-top:20px;">
          Bu mail QMM Talimat Hatırlatma otomasyonu tarafından otomatik olarak gönderilmiştir.
        </p>
      </body>
    </html>
    """


def send_email(subject: str, text_body: str, html_body: str, recipients: list[str]) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    mail_from = os.environ.get("MAIL_FROM", user)
    mail_from_name = os.environ.get("MAIL_FROM_NAME", "QMM Talimat Hatırlatma Sistemi")
    reply_to = os.environ.get("REPLY_TO")

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((mail_from_name, mail_from))
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(mail_from, recipients, msg.as_string())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        help="Test amacli bugunun tarihi yerine kullanilacak tarih (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mail gondermeden sadece kimlere ne gonderilecegini yazdirir",
    )
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()

    documents = load_documents(EXCEL_PATH)
    recipients = load_recipients(RECIPIENTS_PATH)
    sent_state = load_state(STATE_PATH)

    due_items = find_due_reminders(documents, today, sent_state)

    if not due_items:
        print(f"[{today}] Bugun icin hatirlatma gereken talimat yok.")
        return

    text_body = build_email_text(due_items, today)
    html_body = build_email_html(due_items, today)
    subject = build_subject(due_items, today)

    print(f"Konu: {subject}\n")
    print(text_body)

    if args.dry_run:
        print(f"\n[DRY RUN] Mail gonderilmedi. Aliciler: {[r['email'] for r in recipients]}")
        return

    if not recipients:
        print("Uyari: config/recipients.json icinde alici yok, mail gonderilmedi.")
        return

    send_email(subject, text_body, html_body, [r["email"] for r in recipients])

    for item in due_items:
        sent_state.add(item["state_key"])
    save_state(STATE_PATH, sent_state)
    print(f"\n{len(due_items)} talimat icin hatirlatma maili gonderildi.")


if __name__ == "__main__":
    main()
