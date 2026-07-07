"""Static HTML status page ("görsel durum sayfası").

Rendered on every run into a folder the QMM team can reach (typically on
the same network share as the Excel). It is a plain self-contained HTML
file - no server, no hosting, no external requests - so the confidential
list never leaves the company network. Status is always conveyed as
icon + label, never color alone; a full table view sits below the chart.
"""

from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path

from .models import Document

# Status roles: key -> (label, icon). Keys are ordered most to least urgent.
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


def _days_text(days: int) -> str:
    if days < 0:
        return f"{-days} gün geçti"
    return "bugün" if days == 0 else f"{days} gün"


def _section_bars(documents: list[Document], today: date) -> str:
    """Horizontal stacked bar per Bölüm, segments colored by status."""
    sections: dict[str, dict[str, int]] = {}
    for d in documents:
        key = status_for((d.due_date - today).days)
        bucket = sections.setdefault(d.section or "-", dict.fromkeys(_STATUS, 0))
        bucket[key] += 1
    if not sections:
        return ""
    # Most urgent sections first, then alphabetical for stability.
    ordered = sorted(
        sections.items(),
        key=lambda kv: (-(kv[1]["critical"] + kv[1]["serious"]), kv[0]),
    )
    max_total = max(sum(c.values()) for c in sections.values())

    rows = []
    for section, counts in ordered:
        total = sum(counts.values())
        segments = []
        for key in _STATUS:
            n = counts[key]
            if not n:
                continue
            label, _icon = _STATUS[key]
            segments.append(
                f"<span class='seg seg-{key}' style='flex-grow:{n}'"
                f" title='{html.escape(section)} · {label}: {n}'></span>"
            )
        width_pct = round(total / max_total * 100)
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-name'>{html.escape(section)}</div>"
            f"<div class='bar-track'><div class='bar' style='width:{width_pct}%'>"
            f"{''.join(segments)}</div>"
            f"<span class='bar-total'>{total}</span></div>"
            "</div>"
        )

    legend = "".join(
        f"<span class='lg'><span class='sw sw-{key}'></span>"
        f"<span class='ic'>{icon}</span> {label}</span>"
        for key, (label, icon) in _STATUS.items()
    )
    return (
        "<section class='panel'>"
        "<h2>Bölüm bazında durum</h2>"
        f"<div class='legend'>{legend}</div>"
        f"<div class='bars'>{''.join(rows)}</div>"
        "</section>"
    )


def render_report(documents: list[Document], today: date, source_name: str) -> str:
    rows = sorted(documents, key=lambda d: d.due_date)
    counts = dict.fromkeys(_STATUS, 0)
    body_rows = []
    for d in rows:
        days = (d.due_date - today).days
        key = status_for(days)
        counts[key] += 1
        label, icon = _STATUS[key]
        search_blob = html.escape(
            f"{d.title} {d.section} {d.prepared_by}".casefold()
        )
        body_rows.append(
            f"<tr data-status='{key}' data-search='{search_blob}'>"
            f"<td>{html.escape(d.title)}</td>"
            f"<td>{html.escape(d.section or '-')}</td>"
            f"<td class='num'>{html.escape(d.revision_no or '-')}</td>"
            f"<td>{html.escape(d.prepared_by or '-')}</td>"
            f"<td class='num'>{d.revision_date.strftime('%d.%m.%Y') if d.revision_date else '-'}</td>"
            f"<td class='num'>{d.due_date.strftime('%d.%m.%Y')}</td>"
            f"<td class='num'>{_days_text(days)}</td>"
            f"<td><span class='st st-{key}'><span class='ic'>{icon}</span>{label}</span></td>"
            "</tr>"
        )

    tiles = []
    for key, (label, icon) in _STATUS.items():
        tiles.append(
            f"<div class='tile t-{key}'>"
            f"<div class='tile-num'>{counts[key]}</div>"
            f"<div class='tile-label'><span class='ic'>{icon}</span> {label}</div>"
            "</div>"
        )

    chips = ["<button class='chip active' data-filter='all'>Tümü</button>"]
    for key, (label, icon) in _STATUS.items():
        chips.append(
            f"<button class='chip' data-filter='{key}'>"
            f"<span class='ic'>{icon}</span> {label}</button>"
        )

    generated = datetime.now().strftime("%d.%m.%Y %H:%M")
    status_labels_js = json.dumps(
        {k: v[0] for k, v in _STATUS.items()}, ensure_ascii=False
    )
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
  h2 {{ font-size: .95rem; margin: 0 0 .8rem; }}
  .sub {{ color: var(--ink-soft); font-size: .85rem; margin: 0 0 1.6rem; }}
  .panel {{ background: var(--panel); border: 1px solid var(--line);
           border-radius: 8px; padding: 1rem 1.15rem 1.15rem;
           margin-bottom: 1.4rem; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
           gap: .8rem; margin-bottom: 1.4rem; }}
  .tile {{ background: var(--panel); border: 1px solid var(--line);
          border-radius: 8px; padding: .85rem 1rem; }}
  .tile-num {{ font-size: 1.9rem; font-weight: 650; line-height: 1.15;
              font-variant-numeric: tabular-nums; }}
  .tile-label {{ font-size: .78rem; color: var(--ink-soft); }}
  .t-critical .tile-num {{ color: var(--critical); }}
  .t-serious  .tile-num {{ color: var(--serious); }}
  .t-warning  .tile-num {{ color: var(--warning); }}
  .t-good     .tile-num {{ color: var(--good); }}

  /* section bars */
  .legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1.1rem;
            font-size: .74rem; color: var(--ink-soft); margin-bottom: .9rem; }}
  .lg {{ display: inline-flex; align-items: center; gap: .35em; }}
  .sw {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
  .sw-critical {{ background: var(--critical); }}
  .sw-serious  {{ background: var(--serious); }}
  .sw-warning  {{ background: var(--warning); }}
  .sw-good     {{ background: var(--good); }}
  .bars {{ display: flex; flex-direction: column; gap: .55rem; }}
  .bar-row {{ display: grid; grid-template-columns: 150px 1fr; gap: .8rem;
             align-items: center; font-size: .8rem; }}
  .bar-name {{ text-align: right; color: var(--ink-soft);
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .bar-track {{ display: flex; align-items: center; gap: .5rem; }}
  .bar {{ display: flex; gap: 2px; height: 16px; min-width: 16px; }}
  .seg {{ display: block; }}
  .bar .seg:first-child {{ border-radius: 4px 0 0 4px; }}
  .bar .seg:last-child  {{ border-radius: 0 4px 4px 0; }}
  .bar .seg:only-child  {{ border-radius: 4px; }}
  .seg-critical {{ background: var(--critical); }}
  .seg-serious  {{ background: var(--serious); }}
  .seg-warning  {{ background: var(--warning); }}
  .seg-good     {{ background: var(--good); }}
  .bar-total {{ font-size: .74rem; color: var(--ink-soft);
               font-variant-numeric: tabular-nums; }}

  /* filters */
  .controls {{ display: flex; flex-wrap: wrap; gap: .5rem;
              align-items: center; margin-bottom: .8rem; }}
  .search {{ flex: 1 1 220px; max-width: 320px; padding: .45rem .7rem;
            border: 1px solid var(--line); border-radius: 6px;
            background: var(--panel); color: var(--ink); font: inherit;
            font-size: .84rem; }}
  .search:focus {{ outline: 2px solid var(--ink-soft); outline-offset: 1px; }}
  .chip {{ border: 1px solid var(--line); background: var(--panel);
          color: var(--ink-soft); border-radius: 99px; padding: .3rem .75rem;
          font: inherit; font-size: .76rem; cursor: pointer; }}
  .chip .ic {{ font-size: .85em; }}
  .chip.active {{ border-color: var(--ink-soft); color: var(--ink);
                 font-weight: 600; }}
  .chip:focus-visible {{ outline: 2px solid var(--ink-soft); outline-offset: 1px; }}

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
  .empty {{ padding: 1rem; color: var(--ink-soft); font-size: .84rem;
           display: none; }}
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

  {_section_bars(rows, today)}

  <section class="panel">
    <h2>Talimat listesi</h2>
    <div class="controls">
      <input class="search" id="q" type="search"
             placeholder="Ara: doküman, bölüm, hazırlayan…"
             aria-label="Tabloda ara">
      {''.join(chips)}
    </div>
    <div class="tbl">
      <table>
        <thead><tr>
          <th>Doküman</th><th>Bölüm</th><th>Rev. No</th><th>Hazırlayan</th>
          <th>Son Revizyon</th><th>Son Geçerlilik</th><th>Kalan Süre</th><th>Durum</th>
        </tr></thead>
        <tbody id="rows">{''.join(body_rows)}</tbody>
      </table>
      <p class="empty" id="empty">Bu filtreyle eşleşen talimat yok.</p>
    </div>
  </section>

  <footer>Bu sayfa QMM hatırlatma otomasyonu tarafından üretilir; yalnızca şirket
  ağındaki bu klasörde durur, hiçbir dış sisteme yüklenmez. Gizli “Revizyon
  İçeriği” alanı bu sayfada yer almaz.</footer>
</main>
<script>
  var STATUS_LABELS = {status_labels_js};
  var q = document.getElementById("q");
  var rows = Array.prototype.slice.call(
      document.getElementById("rows").querySelectorAll("tr"));
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  var empty = document.getElementById("empty");
  var activeFilter = "all";

  function apply() {{
    var text = q.value.trim().toLocaleLowerCase("tr");
    var visible = 0;
    rows.forEach(function (tr) {{
      var okStatus = activeFilter === "all" ||
                     tr.getAttribute("data-status") === activeFilter;
      var okText = !text ||
                   tr.getAttribute("data-search").indexOf(text) !== -1;
      var show = okStatus && okText;
      tr.style.display = show ? "" : "none";
      if (show) visible++;
    }});
    empty.style.display = visible ? "none" : "block";
  }}

  q.addEventListener("input", apply);
  chips.forEach(function (chip) {{
    chip.addEventListener("click", function () {{
      chips.forEach(function (c) {{ c.classList.remove("active"); }});
      chip.classList.add("active");
      activeFilter = chip.getAttribute("data-filter");
      apply();
    }});
  }});
</script>
</body>
</html>
"""


def write_report(path: Path, documents: list[Document], today: date,
                 source_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(documents, today, source_name), encoding="utf-8")
