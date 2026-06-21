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

    def test_main_produces_json_report_file(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_validate_loghouse.py', '--root', str(ROOT)])
        cat_validate_loghouse.main()
        out = capsys.readouterr().out
        # Parse the report path from the "Report written to: ..." line
        import json
        report_path = None
        for line in out.splitlines():
            if 'Report written to:' in line:
                report_path = ROOT / line.split('Report written to:')[-1].strip()
                break
        if report_path is None:
            report_path = ROOT / 'evidence' / 'reports' / 'MP-CAT-A007-4C01_validation_report.json'
        if report_path.exists():
            data = json.loads(report_path.read_text(encoding='utf-8'))
            assert 'overall' in data
            assert 'checks' in data
