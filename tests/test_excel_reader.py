from datetime import date, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from qmm_reminder.config import ExcelConfig
from qmm_reminder.excel_reader import (
    ExcelReadError,
    add_years,
    read_documents,
    read_recipients,
)

HEADERS = [
    "Bölüm",
    "Revizyon No",
    "Revizyon Tarihi",
    "Hazırlayan",
    "Revizyon İçeriği",
    "Değişiklik Olmaması Durumunda Güncellenmesi Gereken İlk Tarih",
    "Onay Dokümanı",
]


def make_cfg(path: Path) -> ExcelConfig:
    return ExcelConfig(
        path=str(path),
        sheet=None,
        columns={
            "section": "Bölüm",
            "revision_no": "Revizyon No",
            "revision_date": "Revizyon Tarihi",
            "prepared_by": "Hazırlayan",
            "due_date": HEADERS[5],
            "approval_doc": "Onay Dokümanı",
        },
        id_columns=["section", "approval_doc"],
    )


def write_xlsx(path: Path, rows, headers=HEADERS, title_row_first=False):
    wb = Workbook()
    ws = wb.active
    if title_row_first:
        ws.append(["QMM Working Instructions Control List"])
        ws.append([])
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_reads_rows_and_dates(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    write_xlsx(f, [
        ["Üretim", "02", datetime(2023, 8, 1), "A. Yılmaz", "gizli içerik",
         datetime(2026, 8, 1), "QMM-TL-002-ONAY"],
        ["Lojistik", "01", "15.03.2024", "B. Demir", "gizli içerik",
         "15.03.2027", "QMM-TL-004-ONAY"],
    ])
    docs, warnings = read_documents(make_cfg(f), validity_years=3)
    assert warnings == []
    assert len(docs) == 2
    assert docs[0].section == "Üretim"
    assert docs[0].due_date == date(2026, 8, 1)
    assert docs[0].revision_date == date(2023, 8, 1)
    assert docs[1].due_date == date(2027, 3, 15)  # dd.mm.yyyy string parsed
    assert docs[0].title == "QMM-TL-002-ONAY"


def test_empty_due_falls_back_to_revision_plus_validity(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    write_xlsx(f, [
        ["Bakım", "01", datetime(2024, 2, 29), "C. Kaya", "x", None, "DOC-1"],
    ])
    docs, warnings = read_documents(make_cfg(f), validity_years=3)
    assert warnings == []
    assert docs[0].due_date == date(2027, 2, 28)  # leap-day handled


def test_unusable_row_is_warned_not_fatal(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    write_xlsx(f, [
        ["Bakım", "01", None, "C. Kaya", "x", None, "DOC-1"],  # no dates at all
        ["Üretim", "01", datetime(2024, 1, 1), "A", "x",
         datetime(2027, 1, 1), "DOC-2"],
    ])
    docs, warnings = read_documents(make_cfg(f), validity_years=3)
    assert len(docs) == 1
    assert len(warnings) == 1
    assert "Row 2" in warnings[0]


def test_header_found_below_a_title_row(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    write_xlsx(f, [
        ["Üretim", "01", datetime(2024, 1, 1), "A", "x",
         datetime(2027, 1, 1), "DOC-2"],
    ], title_row_first=True)
    docs, _ = read_documents(make_cfg(f), validity_years=3)
    assert len(docs) == 1


def test_same_identity_same_doc_id(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    write_xlsx(f, [
        ["Üretim", "01", datetime(2024, 1, 1), "A", "x",
         datetime(2027, 1, 1), "DOC-2"],
        ["üretim", "02", datetime(2025, 1, 1), "B", "y",
         datetime(2028, 1, 1), "doc-2"],  # same identity, different case
        ["Lojistik", "01", datetime(2024, 1, 1), "A", "x",
         datetime(2027, 1, 1), "DOC-2"],
    ])
    docs, _ = read_documents(make_cfg(f), validity_years=3)
    assert docs[0].doc_id == docs[1].doc_id
    assert docs[0].doc_id != docs[2].doc_id


def test_missing_required_header_raises(tmp_path: Path):
    f = tmp_path / "list.xlsx"
    headers = [h if h != "Bölüm" else "Departman" for h in HEADERS]
    write_xlsx(f, [], headers=headers)
    with pytest.raises(ExcelReadError):
        read_documents(make_cfg(f), validity_years=3)


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(ExcelReadError):
        read_documents(make_cfg(tmp_path / "nope.xlsx"), validity_years=3)


def test_add_years():
    assert add_years(date(2023, 8, 1), 3) == date(2026, 8, 1)
    assert add_years(date(2024, 2, 29), 3) == date(2027, 2, 28)


def write_recipients_sheet(path: Path, rows, headers=("Ad", "E-posta", "Aktif")):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bildirim Alıcıları"
    ws.append(list(headers))
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_recipients_active_invalid_and_duplicates(tmp_path: Path):
    f = tmp_path / "r.xlsx"
    write_recipients_sheet(f, [
        ["Çağlar Yılmaz", "caglar@example.com", "Evet"],
        ["", "ekip@example.com", ""],                 # no name -> local part
        ["Ayrılan", "eski@example.com", "Hayır"],     # deactivated
        ["Bozuk", "adres-degil", ""],                 # invalid -> warning
        ["Tekrar", "CAGLAR@example.com", "Evet"],     # duplicate, other case
        ["Boş", None, ""],                            # skipped silently
    ])
    people, warnings = read_recipients(f, "Bildirim Alıcıları")
    assert people == [
        ("Çağlar Yılmaz", "caglar@example.com"),
        ("ekip", "ekip@example.com"),
    ]
    assert len(warnings) == 1 and "adres-degil" in warnings[0]


def test_recipients_missing_sheet_is_warning(tmp_path: Path):
    f = tmp_path / "r.xlsx"
    write_recipients_sheet(f, [])
    people, warnings = read_recipients(f, "Alıcılar")
    assert people == []
    assert len(warnings) == 1 and "Alıcılar" in warnings[0]


def test_recipients_sheet_name_case_insensitive(tmp_path: Path):
    f = tmp_path / "r.xlsx"
    write_recipients_sheet(f, [["Lider", "lider@example.com", "Evet"]])
    people, warnings = read_recipients(f, "bildirim alıcıları")
    assert people == [("Lider", "lider@example.com")]
    assert warnings == []
