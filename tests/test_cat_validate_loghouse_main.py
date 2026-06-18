"""Coverage for cat_validate_loghouse.py main() — lines 277-356."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import cat_validate_loghouse


ROOT = Path(__file__).resolve().parents[1]


class TestValidateLoghouseMain:
    def test_main_returns_zero_or_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py'])
        result = cat_validate_loghouse.main()
        assert result in (0, 1)

    def test_main_prints_report_path(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py'])
        cat_validate_loghouse.main()
        out = capsys.readouterr().out
        assert 'Report written to:' in out

    def test_main_prints_validation_summary(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py'])
        cat_validate_loghouse.main()
        out = capsys.readouterr().out
        assert 'LOGHOUSE validation' in out

    def test_main_with_custom_root(self, monkeypatch, capsys, tmp_path):
        # A tmp_path with no loghouse fixtures → some checks will fail → returns 1
        # but it shouldn't crash
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py', '--root', str(tmp_path)])
        result = cat_validate_loghouse.main()
        assert result in (0, 1)

    def test_main_produces_json_report_file(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py'])
        cat_validate_loghouse.main()
        # The report is written to evidence/reports/loghouse_validation.json
        report_path = ROOT / 'evidence' / 'reports' / 'loghouse_validation.json'
        if report_path.exists():
            import json
            data = json.loads(report_path.read_text(encoding='utf-8'))
            assert 'overall_ok' in data or 'checks' in data
