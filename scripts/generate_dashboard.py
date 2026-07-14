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

from check_reminders import (
    EXCEL_PATH,
    RECIPIENTS_PATH,
    build_email_html,
    build_subject,
    load_documents,
    load_recipients,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "dashboard.html"

DASHBOARD_TITLE = "QMM Talimat Takip Sistemi"

# Referans gorseldeki spektrumdan orneklenen renk paleti (kirmizidan
# yesile). Baslik gradyani ve bolum rozetleri icin kullanilir.
SPECTRUM_PALETTE = [
    "#C81E3A",  # kirmizi
    "#9C2B6E",  # magenta
    "#6B3FA0",  # mor
    "#3E4C9C",  # indigo
    "#1E5FA8",  # mavi
    "#1C8FC0",  # gok mavisi
    "#1CB4C9",  # camgobegi
    "#14A085",  # deniz yesili
    "#2E9E3F",  # yesil
    "#8FC93F",  # sari-yesil
]

# (ust_sinir_gun, etiket, arka_plan_rengi, yazi_rengi)
# NOT: aciliyet renkleri evrensel anlam tasidigi (kirmizi=kritik, yesil=normal)
# icin spektrum paletinden degil, sabit kirmizi/turuncu/sari/yesil tonlarindan
# secildi -- boylece durum okunabilirligi bozulmuyor.
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


def render_html(documents: list[dict], today: date, recipients: list[dict]) -> str:
    rows_data = build_rows(documents, today)
    recipients_json = json.dumps(recipients, ensure_ascii=False)

    counts: dict[str, int] = {}
    for r in rows_data:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    departments = sorted({r["bolum"] for r in rows_data if r["bolum"]})
    dept_colors = {d: SPECTRUM_PALETTE[i % len(SPECTRUM_PALETTE)] for i, d in enumerate(departments)}

    summary_cards = "".join(
        f"""
        <button class="card" data-filter="{label}" style="background:{bg};color:{fg};">
          <div class="card-count">{counts.get(label, 0)}</div>
          <div class="card-label">{label}</div>
        </button>"""
        for _, label, bg, fg in STATUS_BANDS
    )

    dept_chips = "".join(
        f"""<button class="dept-chip" data-dept="{d}" style="border-color:{dept_colors[d]};color:{dept_colors[d]};">
          <span class="dot" style="background:{dept_colors[d]};"></span>{d}
        </button>"""
        for d in departments
    )

    rows_json = json.dumps(
        [
            {
                "talimat": r["talimat"],
                "bolum": r["bolum"],
                "bolumRengi": dept_colors.get(r["bolum"], "#6b7280"),
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

    header_gradient = ", ".join(SPECTRUM_PALETTE)

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>{DASHBOARD_TITLE}</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif; color:#1a1a1a; background:#f5f5f5;
    margin:0; padding:0;
  }}
  header {{
    background-image: linear-gradient(100deg, rgba(0,0,0,.58), rgba(0,0,0,.28)),
                       linear-gradient(100deg, {header_gradient});
    color:#fff; padding:28px 40px;
    display:flex; align-items:flex-start; justify-content:space-between; gap:18px; flex-wrap:wrap;
  }}
  .header-left {{ display:flex; align-items:center; gap:18px; }}
  .logo-chip {{
    background:#fff; border-radius:10px; padding:10px 16px; display:flex; align-items:center;
    gap:10px; flex-shrink:0;
  }}
  .logo-chip svg {{ width:34px; height:34px; flex-shrink:0; }}
  .logo-chip .wordmark {{
    font-weight:900; font-size:20px; letter-spacing:0.01em; color:#EC0016; font-family:Arial, Helvetica, sans-serif;
  }}
  .header-divider {{ width:1px; align-self:stretch; background:rgba(255,255,255,.35); }}
  header h1 {{ margin:0; font-size:24px; }}
  header .subtitle {{ color:#f1f1f1; font-size:14px; margin-top:6px; }}
  header .meta {{ color:#e2e2e2; font-size:12px; margin-top:14px; }}

  .admin-panel {{
    background:rgba(255,255,255,.96); color:#1a1a1a; border-radius:12px; padding:14px 16px;
    min-width:260px; box-shadow:0 6px 18px rgba(0,0,0,.2);
  }}
  .admin-panel-title {{
    font-size:12px; text-transform:uppercase; letter-spacing:0.04em; color:#6b7280;
    font-weight:bold; margin-bottom:10px; display:flex; align-items:center; gap:6px;
  }}
  .admin-panel-title .badge {{
    background:#3E4C9C; color:#fff; border-radius:10px; padding:1px 8px; font-size:10px;
  }}
  .admin-recipients {{ display:flex; flex-direction:column; gap:6px; margin-bottom:10px; max-height:120px; overflow-y:auto; }}
  .admin-recipient {{
    display:flex; align-items:center; justify-content:space-between; gap:8px;
    background:#f3f4f6; border-radius:8px; padding:5px 8px; font-size:12px;
  }}
  .admin-recipient .remove-btn {{
    border:none; background:none; color:#9ca3af; cursor:pointer; font-size:14px; line-height:1;
    padding:0 2px;
  }}
  .admin-recipient .remove-btn:hover {{ color:#dc2626; }}
  .admin-add-row {{ display:flex; gap:6px; }}
  .admin-add-row input {{
    flex:1; padding:7px 10px; border:1px solid #d1d5db; border-radius:8px; font-size:12px; min-width:0;
  }}
  .admin-add-row button {{
    background:#3E4C9C; color:#fff; border:none; border-radius:8px; padding:7px 12px;
    font-size:12px; font-weight:bold; cursor:pointer; white-space:nowrap;
  }}
  .admin-add-row button:hover {{ background:#2f3a78; }}
  main {{ max-width:1100px; margin:0 auto; padding:32px 40px 60px; }}
  section {{ margin-bottom:44px; }}
  section h2 {{
    font-size:16px; text-transform:uppercase; letter-spacing:0.04em; color:#3E4C9C;
    border-bottom:2px solid #3E4C9C; padding-bottom:8px; margin-bottom:20px;
  }}

  .cards {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .card {{
    border:none; border-radius:10px; padding:16px 22px; min-width:130px; cursor:pointer;
    font-family:inherit; text-align:left; transition:transform .12s ease, box-shadow .12s ease;
  }}
  .card:hover {{ transform:translateY(-2px); box-shadow:0 4px 10px rgba(0,0,0,.12); }}
  .card.active {{ outline:3px solid #1a1a1a; }}
  .card-count {{ font-size:28px; font-weight:bold; }}
  .card-label {{ font-size:13px; margin-top:2px; }}

  .toolbar {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:12px; align-items:center; }}
  .toolbar input {{
    padding:9px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px;
    flex:1; min-width:220px;
  }}
  .toolbar button.reset {{
    padding:9px 14px; border-radius:8px; border:1px solid #d1d5db; background:#fff; cursor:pointer;
  }}

  .dept-chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }}
  .dept-chip {{
    display:inline-flex; align-items:center; gap:6px; background:#fff; border:1.5px solid;
    border-radius:16px; padding:5px 12px; font-size:12px; font-weight:bold; cursor:pointer;
    font-family:inherit;
  }}
  .dept-chip .dot {{ width:8px; height:8px; border-radius:50%; }}
  .dept-chip.active {{ color:#fff !important; }}
  .dept-chip.active .dot {{ background:#fff !important; }}

  table {{ border-collapse:collapse; width:100%; background:#fff; border:1px solid #e5e7eb; border-radius:10px; overflow:hidden; }}
  thead tr {{ background:#f3f4f6; text-align:left; }}
  th {{ padding:12px; cursor:pointer; user-select:none; white-space:nowrap; }}
  th:hover {{ color:#3E4C9C; }}
  td {{ padding:10px 12px; border-bottom:1px solid #e5e7eb; font-size:14px; }}
  .pill {{ display:inline-block; padding:3px 10px; border-radius:12px; font-weight:bold; font-size:12px; }}
  .dept-pill {{ display:inline-flex; align-items:center; gap:6px; font-size:13px; }}
  .dept-pill .dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
  #empty-state {{ text-align:center; color:#6b7280; padding:30px; display:none; }}

  .flow {{ display:flex; gap:0; flex-wrap:wrap; }}
  .flow-step {{
    flex:1; min-width:200px; background:#fff; border:1px solid #e5e7eb; border-radius:10px;
    padding:18px; position:relative; margin-right:28px; margin-bottom:16px;
  }}
  .flow-step:last-child {{ margin-right:0; }}
  .flow-step:not(:last-child)::after {{
    content:"→"; position:absolute; right:-24px; top:50%; transform:translateY(-50%);
    font-size:20px; color:#3E4C9C; font-weight:bold;
  }}
  .flow-num {{
    width:28px; height:28px; border-radius:50%; background:#3E4C9C; color:#fff;
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
    <div class="header-left">
      <div class="logo-chip">
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#58595B" stroke-width="5"/>
          <rect x="26" y="18" width="15" height="64" rx="7.5" fill="none" stroke="#58595B" stroke-width="5"/>
          <rect x="59" y="18" width="15" height="64" rx="7.5" fill="none" stroke="#58595B" stroke-width="5"/>
          <rect x="30" y="47" width="40" height="6" fill="#58595B"/>
        </svg>
        <span class="wordmark">BOSCH</span>
      </div>
      <div class="header-divider"></div>
      <div>
        <h1>{DASHBOARD_TITLE}</h1>
        <div class="subtitle">Kalite Bölümü (QMM) &middot; Çalışma Talimatları Geçerlilik Takibi</div>
        <div class="meta">Son güncelleme: {today.strftime('%d.%m.%Y')} &middot; Toplam {len(rows_data)} talimat izleniyor</div>
      </div>
    </div>

    <div class="admin-panel">
      <div class="admin-panel-title">Yönetici Paneli <span class="badge">Admin</span></div>
      <div class="admin-recipients" id="admin-recipients"></div>
      <div class="admin-add-row">
        <input type="email" id="admin-email-input" placeholder="ornek@tr.bosch.com">
        <button id="admin-add-btn">Ekle</button>
      </div>
    </div>
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
        <button class="reset" id="reset-filters">Filtreleri temizle</button>
      </div>
      <div class="dept-chips" id="dept-chips">{dept_chips}
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
    // NOT: Bu liste sadece sayfa acikken tarayici hafizasinda tutulur, kalici
    // olarak hicbir yere kaydedilmez (demo/gorsel amaclidir). Gercek alici
    // listesi hala config/recipients.json uzerinden yonetiliyor.
    let recipients = {recipients_json};

    function renderRecipients() {{
      const container = document.getElementById('admin-recipients');
      if (!recipients.length) {{
        container.innerHTML = '<div style="color:#9ca3af;font-size:12px;">Henüz alıcı yok</div>';
        return;
      }}
      container.innerHTML = recipients.map((r, i) => `
        <div class="admin-recipient">
          <span>${{r.name ? r.name + ' &middot; ' : ''}}${{r.email}}</span>
          <button class="remove-btn" data-index="${{i}}" title="Kaldır">✕</button>
        </div>
      `).join('');
      container.querySelectorAll('.remove-btn').forEach(btn => {{
        btn.addEventListener('click', () => {{
          recipients.splice(Number(btn.dataset.index), 1);
          renderRecipients();
        }});
      }});
    }}

    document.getElementById('admin-add-btn').addEventListener('click', () => {{
      const input = document.getElementById('admin-email-input');
      const email = input.value.trim();
      if (!email || !email.includes('@')) {{
        input.focus();
        return;
      }}
      recipients.push({{ name: '', email }});
      input.value = '';
      renderRecipients();
    }});
    document.getElementById('admin-email-input').addEventListener('keydown', (e) => {{
      if (e.key === 'Enter') document.getElementById('admin-add-btn').click();
    }});
    renderRecipients();

    const rows = {rows_json};
    let activeStatus = null;
    let activeDept = null;
    let sortKey = 'gun';
    let sortAsc = true;

    function renderTable() {{
      const q = document.getElementById('search').value.toLocaleLowerCase('tr');

      let filtered = rows.filter(r => {{
        if (activeStatus && r.label !== activeStatus) return false;
        if (activeDept && r.bolum !== activeDept) return false;
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
          <td><span class="dept-pill"><span class="dot" style="background:${{r.bolumRengi}};"></span>${{r.bolum}}</span></td>
          <td>${{r.tarih}}</td>
          <td>${{r.gun}} gün</td>
          <td><span class="pill" style="background:${{r.bg}};color:${{r.fg}};">${{r.label}}</span></td>
        </tr>
      `).join('');

      document.getElementById('empty-state').style.display = filtered.length ? 'none' : 'block';
    }}

    document.getElementById('search').addEventListener('input', renderTable);
    document.getElementById('reset-filters').addEventListener('click', () => {{
      document.getElementById('search').value = '';
      activeStatus = null;
      activeDept = null;
      document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
      document.querySelectorAll('.dept-chip').forEach(c => {{
        c.classList.remove('active');
        c.style.background = '#fff';
      }});
      renderTable();
    }});

    document.querySelectorAll('.card').forEach(card => {{
      card.addEventListener('click', () => {{
        const label = card.dataset.filter;
        activeStatus = (activeStatus === label) ? null : label;
        document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
        if (activeStatus) card.classList.add('active');
        renderTable();
      }});
    }});

    document.querySelectorAll('.dept-chip').forEach(chip => {{
      chip.addEventListener('click', () => {{
        const dept = chip.dataset.dept;
        const color = chip.style.borderColor;
        document.querySelectorAll('.dept-chip').forEach(c => {{
          c.classList.remove('active');
          c.style.background = '#fff';
        }});
        if (activeDept === dept) {{
          activeDept = null;
        }} else {{
          activeDept = dept;
          chip.classList.add('active');
          chip.style.background = color;
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
    recipients = load_recipients(RECIPIENTS_PATH)
    html = render_html(documents, today, recipients)
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard olusturuldu: {output_path}")


if __name__ == "__main__":
    main()
