from pathlib import Path

import pytest

from qmm_reminder.config import ConfigError, load_config

MINIMAL = """
excel:
  path: "list.xlsx"
  columns:
    section: "Bölüm"
    revision_date: "Revizyon Tarihi"
    due_date: "Son Tarih"
  id_columns: [section]
notifications:
  teams:
    enabled: true
    mentions:
      - name: "Çağlar Yılmaz"
        email: "caglar@example.com"
      - email: "ulvi@example.com"
"""


def write_cfg(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_mentions_parsed_with_name_fallback(tmp_path: Path):
    cfg = load_config(write_cfg(tmp_path, MINIMAL))
    assert cfg.teams.mentions == [
        ("Çağlar Yılmaz", "caglar@example.com"),
        ("ulvi", "ulvi@example.com"),
    ]
    assert cfg.recipients_sheet is None


def test_invalid_mention_entry_rejected(tmp_path: Path):
    broken = MINIMAL.replace('- email: "ulvi@example.com"', '- "ulvi@example.com"')
    with pytest.raises(ConfigError, match="mentions"):
        load_config(write_cfg(tmp_path, broken))


def test_email_needs_recipients_or_sheet(tmp_path: Path):
    text = MINIMAL + """
  email:
    enabled: true
    smtp_host: "smtp.example.com"
"""
    with pytest.raises(ConfigError, match="recipients"):
        load_config(write_cfg(tmp_path, text))
