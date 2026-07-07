"""Static HTML status page ("görsel durum sayfası").

Rendered on every run into a folder the QMM team can reach (typically on
the same network share as the Excel). It is a plain self-contained HTML
file - no server, no hosting, no external requests - so the confidential
list never leaves the company network. Status is always conveyed as
icon + label, never color alone.
"""

from __future__ import annotations

import html
from datetime import date, datetime
from pathlib import Path

from .models import Document

# Status roles: (key, label, icon)
_STATUS = {
    "critical": ("Süresi doldu", "⛔"),
    "serious": ("Kritik – 7 gün içinde", "▲"),
    "warning": ("Yaklaşıyor – 30 gün içinde", "●"),
    "good": ("Güncel", "✓"),
}


def status_for(days_left: int) -> str:
    if days_left < 0:
        return "critical"
    if days_left <= 7:
        return "serious"
    if days_left <= 30:
        return "warning"
    return "good"


def render_report(documents: list[Document], today: date, source_name: str) -> str:
    rows = sorted(documents, key=lambda d: d.due_date)
    counts = {k: 0 for k in _STATUS}
    body_rows = []
    for d in rows:
        days = (d.due_date - today).days
        key = status_for(days)
        counts[key] += 1
        label, icon = _STATUS[key]
        days_text = (
            f"{-days} gün geçti" if days < 0
            else ("bugün" if days == 0 else f"{days} gün")
        )
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(d.title)}</td>"
            f"<td>{html.escape(d.section or '-')}</td>"
            f"<td class='num'>{html.escape(d.revision_no or '-')}</td>"
            f"<td>{html.escape(d.prepared_by or '-')}</td>"
            f"<td class='num'>{d.revision_date.strftime('%d.%m.%Y') if d.revision_date else '-'}</td>"
            f"<td class='num'>{d.due_date.strftime('%d.%m.%Y')}</td>"
            f"<td class='num'>{days_text}</td>"
            f"<td><span class='st st-{key}'><span class='ic'>{icon}</span>{label}</span></td>"
            "</tr>"
        )

    tiles = []
    for key in ("critical", "serious", "warning", "good"):
        label, icon = _STATUS[key]
        tiles.append(
            f"<div class='tile t-{key}'>"
            f"<div class='tile-num'>{counts[key]}</div>"
            f"<div class='tile-label'><span class='ic'>{icon}</span> {label}</div>"
            "</div>"
        )

    generated = datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QMM Talimat Durum Sayfası</title>
<style>
  :root {{
    --bg: #fcfcfb; --ink: #21252c; --ink-soft: #5c6472; --line: #e3e4e0;
    --panel: #ffffff;
    --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1a1a19; --ink: #e8e8e5; --ink-soft: #a0a29d; --line: #33342f;
      --panel: #222320;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem 1.25rem 3rem;
    background: var(--bg); color: var(--ink);
    font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.5;
  }}
  main {{ max-width: 1060px; margin: 0 auto; }}
  h1 {{ font-size: 1.35rem; margin: 0 0 .2rem; }}
  .sub {{ color: var(--ink-soft); font-size: .85rem; margin: 0 0 1.6rem; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
           gap: .8rem; margin-bottom: 1.8rem; }}
  .tile {{ background: var(--panel); border: 1px solid var(--line);
          border-radius: 8px; padding: .85rem 1rem; }}
  .tile-num {{ font-size: 1.9rem; font-weight: 650; line-height: 1.15;
              font-variant-numeric: tabular-nums; }}
  .tile-label {{ font-size: .78rem; color: var(--ink-soft); }}
  .t-critical .tile-num {{ color: var(--critical); }}
  .t-serious  .tile-num {{ color: var(--serious); }}
  .t-warning  .tile-num {{ color: var(--warning); }}
  .t-good     .tile-num {{ color: var(--good); }}
  .tbl {{ overflow-x: auto; background: var(--panel);
         border: 1px solid var(--line); border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .84rem; }}
  th, td {{ text-align: left; padding: .5rem .8rem; white-space: nowrap; }}
  th {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .06em;
       color: var(--ink-soft); border-bottom: 1px solid var(--line); }}
  td {{ border-bottom: 1px solid var(--line); }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ font-variant-numeric: tabular-nums; }}
  .st {{ display: inline-flex; align-items: center; gap: .35em;
        font-size: .76rem; font-weight: 600; }}
  .st .ic {{ font-size: .8em; }}
  .st-critical {{ color: var(--critical); }}
  .st-serious  {{ color: var(--serious); }}
  .st-warning  {{ color: var(--warning); }}
  .st-good     {{ color: var(--good); }}
  @media (prefers-color-scheme: light) {{
    /* warning/serious are sub-3:1 on light by design; the icon+label pair
       carries the meaning, and the label ink stays readable */
    .st-warning, .st-serious {{ color: var(--ink); }}
    .st-warning .ic {{ color: var(--warning); }}
    .st-serious .ic {{ color: var(--serious); }}
  }}
  footer {{ margin-top: 1.4rem; color: var(--ink-soft); font-size: .76rem;
           max-width: 72ch; }}
</style>
</head>
<body>
<main>
  <h1>QMM Çalışma Talimatları – Geçerlilik Durumu</h1>
  <p class="sub">Kaynak: {html.escape(source_name)} · Oluşturulma: {generated} ·
  Bu sayfa her sabah otomatik yenilenir.</p>
  <div class="tiles">{''.join(tiles)}</div>
  <div class="tbl">
    <table>
      <thead><tr>
        <th>Doküman</th><th>Bölüm</th><th>Rev. No</th><th>Hazırlayan</th>
        <th>Son Revizyon</th><th>Son Geçerlilik</th><th>Kalan Süre</th><th>Durum</th>
      </tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
  <footer>Bu sayfa QMM hatırlatma otomasyonu tarafından üretilir; yalnızca şirket
  ağındaki bu klasörde durur, hiçbir dış sisteme yüklenmez. Gizli “Revizyon
  İçeriği” alanı bu sayfada yer almaz.</footer>
</main>
</body>
</html>
"""


def write_report(path: Path, documents: list[Document], today: date,
                 source_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(documents, today, source_name), encoding="utf-8")
