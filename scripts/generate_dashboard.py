"""QMM Talimat durum dashboard'u olusturur.

data/QMM_Talimat_Index.xlsx dosyasindaki tum talimatlari okuyup, her birinin
son gecerlilik tarihine gore durumunu (suresi gecmis / kritik / yaklasan /
normal) hesaplar ve tek bir kendi kendine yeten (self-contained) HTML dosyasi
uretir. Bu dosya sunucu/Python/kurulum gerektirmeden, cift tiklayip tarayicida
acilabilir.

check_reminders.py'daki mail hatirlatmasindan bagimsiz calisir; o script'in
esik bazli (30/15/7/1 gun) mail mantigina karsilik, bu script her calistiginda
TUM talimatlarin guncel durumunu gosteren bir "anlik goruntu" (snapshot)
olusturur. Ayrica ekip sunumlarinda kullanilmak uzere, gonderilen mailin
gercek gorunumunu de sayfa icinde ornekler.
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from check_reminders import EXCEL_PATH, build_email_html, build_subject, load_documents

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dashboard.html"

# Bosch kurumsal tonlarina yakin renk paleti
BOSCH_RED = "#E2001A"
BOSCH_DARK = "#1A1A1A"

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


def build_rows(documents: list[dict], today: date) -> list[dict]:
    rows_data = []
    for doc in documents:
        days_left = (doc["son_gecerlilik"] - today).days
        label, bg, fg = status_for(days_left)
        rows_data.append({**doc, "days_left": days_left, "label": label, "bg": bg, "fg": fg})
    rows_data.sort(key=lambda d: d["days_left"])
    return rows_data


def render_html(documents: list[dict], today: date) -> str:
    rows_data = build_rows(documents, today)

    counts: dict[str, int] = {}
    for r in rows_data:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    departments = sorted({r["bolum"] for r in rows_data if r["bolum"]})

    summary_cards = "".join(
        f"""
        <button class="card" data-filter="{label}" style="background:{bg};color:{fg};">
          <div class="card-count">{counts.get(label, 0)}</div>
          <div class="card-label">{label}</div>
        </button>"""
        for _, label, bg, fg in STATUS_BANDS
    )

    department_options = "".join(f'<option value="{d}">{d}</option>' for d in departments)

    rows_json = json.dumps(
        [
            {
                "talimat": r["talimat"],
                "bolum": r["bolum"],
                "tarih": r["son_gecerlilik"].strftime("%d.%m.%Y"),
                "gun": r["days_left"],
                "label": r["label"],
                "bg": r["bg"],
                "fg": r["fg"],
            }
            for r in rows_data
        ],
        ensure_ascii=False,
    )

    # Mail onizlemesi icin en aciliyetli 5 talimati ornek al
    sample_items = [r for r in rows_data if r["days_left"] <= 30][:5] or rows_data[:5]
    mail_html = build_email_html(sample_items, today) if sample_items else ""
    mail_subject = build_subject(sample_items, today) if sample_items else ""

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>QMM Talimat Hatırlatma Sistemi</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif; color:{BOSCH_DARK}; background:#f5f5f5;
    margin:0; padding:0;
  }}
  header {{
    background:{BOSCH_DARK}; color:#fff; padding:28px 40px; border-top:6px solid {BOSCH_RED};
  }}
  header h1 {{ margin:0; font-size:24px; }}
  header .subtitle {{ color:#c7c7c7; font-size:14px; margin-top:6px; }}
  header .meta {{ color:#9c9c9c; font-size:12px; margin-top:14px; }}
  main {{ max-width:1100px; margin:0 auto; padding:32px 40px 60px; }}
  section {{ margin-bottom:44px; }}
  section h2 {{
    font-size:16px; text-transform:uppercase; letter-spacing:0.04em; color:{BOSCH_RED};
    border-bottom:2px solid {BOSCH_RED}; padding-bottom:8px; margin-bottom:20px;
  }}

  .cards {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .card {{
    border:none; border-radius:10px; padding:16px 22px; min-width:130px; cursor:pointer;
    font-family:inherit; text-align:left; transition:transform .12s ease, box-shadow .12s ease;
  }}
  .card:hover {{ transform:translateY(-2px); box-shadow:0 4px 10px rgba(0,0,0,.12); }}
  .card.active {{ outline:3px solid {BOSCH_DARK}; }}
  .card-count {{ font-size:28px; font-weight:bold; }}
  .card-label {{ font-size:13px; margin-top:2px; }}

  .toolbar {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; align-items:center; }}
  .toolbar input, .toolbar select {{
    padding:9px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px;
  }}
  .toolbar input {{ flex:1; min-width:220px; }}
  .toolbar button.reset {{
    padding:9px 14px; border-radius:8px; border:1px solid #d1d5db; background:#fff; cursor:pointer;
  }}

  table {{ border-collapse:collapse; width:100%; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }}
  thead tr {{ background:#f3f4f6; text-align:left; }}
  th {{ padding:12px; cursor:pointer; user-select:none; white-space:nowrap; }}
  th:hover {{ color:{BOSCH_RED}; }}
  td {{ padding:10px 12px; border-bottom:1px solid #e5e7eb; font-size:14px; }}
  .pill {{ display:inline-block; padding:3px 10px; border-radius:12px; font-weight:bold; font-size:12px; }}
  #empty-state {{ text-align:center; color:#6b7280; padding:30px; display:none; }}

  .flow {{ display:flex; gap:0; flex-wrap:wrap; }}
  .flow-step {{
    flex:1; min-width:200px; background:#fff; border:1px solid #e5e7eb; border-radius:10px;
    padding:18px; position:relative; margin-right:28px; margin-bottom:16px;
  }}
  .flow-step:last-child {{ margin-right:0; }}
  .flow-step:not(:last-child)::after {{
    content:"→"; position:absolute; right:-24px; top:50%; transform:translateY(-50%);
    font-size:20px; color:{BOSCH_RED}; font-weight:bold;
  }}
  .flow-num {{
    width:28px; height:28px; border-radius:50%; background:{BOSCH_RED}; color:#fff;
    display:flex; align-items:center; justify-content:center; font-weight:bold; margin-bottom:10px;
  }}
  .flow-step h3 {{ font-size:14px; margin:0 0 6px; }}
  .flow-step p {{ font-size:13px; color:#4b5563; margin:0; }}

  .mail-mock {{ border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; background:#fff; }}
  .mail-mock-header {{ background:#f3f4f6; padding:14px 18px; font-size:13px; color:#374151; }}
  .mail-mock-header div {{ margin-bottom:4px; }}
  .mail-mock iframe {{ width:100%; height:420px; border:0; }}
</style>
</head>
<body>
  <header>
    <h1>QMM Talimat Hatırlatma Sistemi</h1>
    <div class="subtitle">Kalite Bölümü (QMM) &middot; Çalışma Talimatları Geçerlilik Takibi</div>
    <div class="meta">Son güncelleme: {today.strftime('%d.%m.%Y')} &middot; Toplam {len(rows_data)} talimat izleniyor</div>
  </header>

  <main>
    <section>
      <h2>Genel Bakış</h2>
      <div class="cards" id="cards">{summary_cards}
      </div>
    </section>

    <section>
      <h2>Talimat Listesi</h2>
      <div class="toolbar">
        <input id="search" type="text" placeholder="Talimat veya bölüm ara...">
        <select id="dept-filter">
          <option value="">Tüm bölümler</option>
          {department_options}
        </select>
        <button class="reset" id="reset-filters">Filtreleri temizle</button>
      </div>
      <table id="table">
        <thead>
          <tr>
            <th data-key="talimat">Talimat Adı</th>
            <th data-key="bolum">Bölüm</th>
            <th data-key="tarih">Son Geçerlilik Tarihi</th>
            <th data-key="gun">Kalan Gün</th>
            <th data-key="label">Durum</th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
      <div id="empty-state">Aramayla eşleşen talimat bulunamadı.</div>
    </section>

    <section>
      <h2>Nasıl Çalışıyor</h2>
      <div class="flow">
        <div class="flow-step">
          <div class="flow-num">1</div>
          <h3>Excel Kaynağı</h3>
          <p>Tek veri kaynağı: mevcut QMM Talimat Index Excel dosyası. Yeni talimat eklendiğinde ekstra bir işlem gerekmez.</p>
        </div>
        <div class="flow-step">
          <div class="flow-num">2</div>
          <h3>Günlük Otomatik Kontrol</h3>
          <p>Her gün otomatik olarak çalışıp her talimatın geçerlilik süresine kalan günü hesaplar.</p>
        </div>
        <div class="flow-step">
          <div class="flow-num">3</div>
          <h3>Mail Hatırlatması</h3>
          <p>Süre 30 / 15 / 7 / 1 gün kaldığında ilgili kişilere otomatik hatırlatma maili gider.</p>
        </div>
        <div class="flow-step">
          <div class="flow-num">4</div>
          <h3>Bu Dashboard</h3>
          <p>Aynı anda bu pano da güncellenir; herkes tüm talimatların anlık durumunu görebilir.</p>
        </div>
      </div>
    </section>

    <section>
      <h2>Örnek Hatırlatma Maili</h2>
      <div class="mail-mock">
        <div class="mail-mock-header">
          <div><strong>Konu:</strong> {mail_subject}</div>
          <div><strong>Kimden:</strong> QMM Talimat Hatırlatma Sistemi</div>
        </div>
        <iframe srcdoc="{mail_html.replace('"', '&quot;')}"></iframe>
      </div>
    </section>
  </main>

  <script>
    const rows = {rows_json};
    let activeFilter = null;
    let sortKey = 'gun';
    let sortAsc = true;

    function renderTable() {{
      const q = document.getElementById('search').value.toLocaleLowerCase('tr');
      const dept = document.getElementById('dept-filter').value;

      let filtered = rows.filter(r => {{
        if (activeFilter && r.label !== activeFilter) return false;
        if (dept && r.bolum !== dept) return false;
        if (q && !(r.talimat.toLocaleLowerCase('tr').includes(q) || r.bolum.toLocaleLowerCase('tr').includes(q))) return false;
        return true;
      }});

      filtered.sort((a, b) => {{
        let va = a[sortKey], vb = b[sortKey];
        if (typeof va === 'string') {{ va = va.toLocaleLowerCase('tr'); vb = vb.toLocaleLowerCase('tr'); }}
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
      }});

      const tbody = document.getElementById('table-body');
      tbody.innerHTML = filtered.map(r => `
        <tr>
          <td>${{r.talimat}}</td>
          <td>${{r.bolum}}</td>
          <td>${{r.tarih}}</td>
          <td>${{r.gun}} gün</td>
          <td><span class="pill" style="background:${{r.bg}};color:${{r.fg}};">${{r.label}}</span></td>
        </tr>
      `).join('');

      document.getElementById('empty-state').style.display = filtered.length ? 'none' : 'block';
    }}

    document.getElementById('search').addEventListener('input', renderTable);
    document.getElementById('dept-filter').addEventListener('change', renderTable);
    document.getElementById('reset-filters').addEventListener('click', () => {{
      document.getElementById('search').value = '';
      document.getElementById('dept-filter').value = '';
      activeFilter = null;
      document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
      renderTable();
    }});

    document.querySelectorAll('.card').forEach(card => {{
      card.addEventListener('click', () => {{
        const label = card.dataset.filter;
        if (activeFilter === label) {{
          activeFilter = null;
          card.classList.remove('active');
        }} else {{
          activeFilter = label;
          document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
          card.classList.add('active');
        }}
        renderTable();
      }});
    }});

    document.querySelectorAll('th[data-key]').forEach(th => {{
      th.addEventListener('click', () => {{
        const key = th.dataset.key;
        if (sortKey === key) {{ sortAsc = !sortAsc; }} else {{ sortKey = key; sortAsc = true; }}
        renderTable();
      }});
    }});

    renderTable();
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
