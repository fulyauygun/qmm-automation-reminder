"""QMM Talimat durum dashboard'u olusturur.

data/QMM_Talimat_Index.xlsx dosyasindaki tum talimatlari okuyup, her birinin
son gecerlilik tarihine gore durumunu (suresi gecmis / kritik / yaklasan /
normal) hesaplar ve tek bir kendi kendine yeten (self-contained) HTML dosyasi
uretir. Bu dosya sunucu/Python/kurulum gerektirmeden, cift tiklayip tarayicida
acilabilir.

check_reminders.py'daki mail hatirlatmasindan bagimsiz calisir; o script'in
esik bazli (30/15/7/1 gun) mail mantigina karsilik, bu script her calistiginda
TUM talimatlarin guncel durumunu gosteren bir "anlik goruntu" (snapshot)
olusturur.
"""

import argparse
from datetime import date, datetime
from pathlib import Path

from check_reminders import EXCEL_PATH, load_documents

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dashboard.html"

# (ust_sinir_gun, etiket, arka_plan_rengi, yazi_rengi)
STATUS_BANDS = [
    (0, "Süresi geçti", "#fee2e2", "#991b1b"),
    (7, "Kritik", "#fee2e2", "#dc2626"),
    (15, "Yaklaşıyor", "#ffedd5", "#c2410c"),
    (30, "Dikkat", "#fef9c3", "#a16207"),
    (None, "Normal", "#dcfce7", "#166534"),
]


def status_for(days_left: int) -> tuple[str, str, str]:
    for upper, label, bg, fg in STATUS_BANDS:
        if upper is None or days_left <= upper:
            return label, bg, fg
    return STATUS_BANDS[-1][1:]


def render_html(documents: list[dict], today: date) -> str:
    rows_data = []
    for doc in documents:
        days_left = (doc["son_gecerlilik"] - today).days
        label, bg, fg = status_for(days_left)
        rows_data.append({**doc, "days_left": days_left, "label": label, "bg": bg, "fg": fg})

    rows_data.sort(key=lambda d: d["days_left"])

    counts: dict[str, int] = {}
    for r in rows_data:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    summary_cards = "".join(
        f"""
        <div style="background:{bg};color:{fg};border-radius:10px;padding:14px 18px;min-width:120px;">
          <div style="font-size:26px;font-weight:bold;">{counts.get(label, 0)}</div>
          <div style="font-size:13px;">{label}</div>
        </div>"""
        for _, label, bg, fg in STATUS_BANDS
    )

    table_rows = "".join(
        f"""
        <tr data-label="{r['label']}">
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{r['talimat']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{r['bolum']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{r['son_gecerlilik'].strftime('%d.%m.%Y')}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
            {r['days_left']} gün
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
            <span style="display:inline-block;padding:3px 10px;border-radius:12px;background:{r['bg']};color:{r['fg']};font-weight:bold;font-size:13px;">
              {r['label']}
            </span>
          </td>
        </tr>"""
        for r in rows_data
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>QMM Talimat Durum Panosu</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; color:#111827; background:#f9fafb; margin:0; padding:24px; }}
  h1 {{ font-size:20px; margin-bottom:4px; }}
  .meta {{ color:#6b7280; font-size:13px; margin-bottom:20px; }}
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; }}
  input#search {{ padding:8px 12px; border:1px solid #d1d5db; border-radius:8px; width:280px; margin-bottom:12px; }}
  table {{ border-collapse:collapse; width:100%; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }}
  thead tr {{ background:#f3f4f6; text-align:left; }}
  th {{ padding:10px 12px; }}
</style>
</head>
<body>
  <h1>QMM Talimat Durum Panosu</h1>
  <div class="meta">Oluşturulma: {today.strftime('%d.%m.%Y')} &middot; Toplam {len(rows_data)} talimat</div>

  <div class="cards">{summary_cards}
  </div>

  <input id="search" type="text" placeholder="Talimat veya bölüm ara...">

  <table id="table">
    <thead>
      <tr>
        <th>Talimat Adı</th>
        <th>Bölüm</th>
        <th>Son Geçerlilik Tarihi</th>
        <th>Kalan Gün</th>
        <th>Durum</th>
      </tr>
    </thead>
    <tbody>{table_rows}
    </tbody>
  </table>

  <script>
    document.getElementById('search').addEventListener('input', function (e) {{
      var q = e.target.value.toLocaleLowerCase('tr');
      document.querySelectorAll('#table tbody tr').forEach(function (tr) {{
        tr.style.display = tr.textContent.toLocaleLowerCase('tr').includes(q) ? '' : 'none';
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Test amacli bugunun tarihi yerine kullanilacak tarih (YYYY-MM-DD)")
    parser.add_argument("--output", help="Cikti dosyasi yolu (varsayilan: dashboard.html)")
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    output_path = Path(args.output) if args.output else OUTPUT_PATH

    documents = load_documents(EXCEL_PATH)
    html = render_html(documents, today)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard olusturuldu: {output_path}")


if __name__ == "__main__":
    main()
