from datetime import date, timedelta
from pathlib import Path

from qmm_reminder.models import Document
from qmm_reminder.report import render_report, status_for, write_report

TODAY = date(2026, 7, 7)


def doc(due: date, title: str) -> Document:
    return Document(
        doc_id=title, title=title, section="Üretim", revision_no="01",
        prepared_by="A. Yılmaz", revision_date=None, due_date=due, source_row=2,
    )


def test_status_thresholds():
    assert status_for(-1) == "critical"
    assert status_for(0) == "serious"
    assert status_for(7) == "serious"
    assert status_for(8) == "warning"
    assert status_for(30) == "warning"
    assert status_for(31) == "good"


def test_render_contains_docs_sorted_and_escaped():
    docs = [
        doc(TODAY + timedelta(days=60), "B<img src=x>"),
        doc(TODAY - timedelta(days=3), "A-doldu"),
    ]
    html = render_report(docs, TODAY, "liste.xlsx")
    assert "Süresi doldu" in html and "Güncel" in html
    assert "&lt;img src=x&gt;" in html and "<img src=x>" not in html
    # overdue row is rendered before the up-to-date one (sorted by due date)
    assert html.index("A-doldu") < html.index("B&lt;img src=x&gt;")
    assert "3 gün geçti" in html


def test_render_has_section_bars_and_filters():
    docs = [
        doc(TODAY - timedelta(days=1), "X1"),
        doc(TODAY + timedelta(days=90), "X2"),
    ]
    html = render_report(docs, TODAY, "liste.xlsx")
    assert "Bölüm bazında durum" in html
    assert "seg-critical" in html and "seg-good" in html
    assert 'data-filter="all"' in html.replace("'", '"')
    assert 'id="q"' in html.replace("'", '"')


def test_write_report_creates_file(tmp_path: Path):
    target = tmp_path / "rapor" / "index.html"
    write_report(target, [doc(TODAY + timedelta(days=5), "X")], TODAY, "liste.xlsx")
    text = target.read_text(encoding="utf-8")
    assert "QMM Çalışma Talimatları" in text and "X" in text
