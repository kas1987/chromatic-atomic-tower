"""Extended coverage for cat_tower_guard.py.

Covers: render_markdown(), write_reports(), run_tower_guard(), and main()
paths not exercised by existing tests.

Import pattern: always ``import cat_tower_guard`` so monkeypatching hits
the correct module namespace.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import cat_tower_guard


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sample_report(status: str = "pass") -> dict:
    return {
        "version": "0.1.0",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "root": "/tmp/root",
        "status": status,
        "checks": [
            {
                "name": "state_alignment",
                "status": status,
                "ok": ["aligned"],
                "issues": [],
            }
        ],
    }


# ===========================================================================
# TestRenderMarkdown
# ===========================================================================

class TestRenderMarkdown:
    def test_renders_header(self):
        out = cat_tower_guard.render_markdown(_sample_report())
        assert "# Tower Guard Report" in out

    def test_renders_ok_section(self):
        report = _sample_report()
        report["checks"][0]["ok"] = ["state aligned"]
        out = cat_tower_guard.render_markdown(report)
        assert "### OK" in out
        assert "state aligned" in out

    def test_renders_issues_section(self):
        report = _sample_report("fail")
        report["checks"][0]["issues"] = ["DRIFT detected"]
        out = cat_tower_guard.render_markdown(report)
        assert "### Issues" in out
        assert "DRIFT detected" in out

    def test_renders_no_issues_when_empty(self):
        report = _sample_report()
        report["checks"][0]["issues"] = []
        out = cat_tower_guard.render_markdown(report)
        assert "### Issues" not in out

    def test_renders_overall_status(self):
        out = cat_tower_guard.render_markdown(_sample_report("fail"))
        assert "fail" in out


# ===========================================================================
# TestWriteReports
# ===========================================================================

class TestWriteReports:
    def test_write_reports_creates_files(self, tmp_path):
        report = _sample_report()
        md_path = tmp_path / "out.md"
        json_path = tmp_path / "out.json"
        cat_tower_guard.write_reports(report, md_path, json_path)
        assert md_path.exists()
        assert json_path.exists()
        # Validate JSON is parseable
        parsed = json.loads(json_path.read_text(encoding="utf-8"))
        assert parsed["status"] == "pass"

    def test_write_reports_creates_parent_dir(self, tmp_path):
        report = _sample_report()
        md_path = tmp_path / "subdir" / "nested" / "out.md"
        json_path = tmp_path / "subdir" / "nested" / "out.json"
        cat_tower_guard.write_reports(report, md_path, json_path)
        assert md_path.exists()
        assert json_path.exists()

    def test_write_reports_md_contains_header(self, tmp_path):
        report = _sample_report()
        md_path = tmp_path / "out.md"
        json_path = tmp_path / "out.json"
        cat_tower_guard.write_reports(report, md_path, json_path)
        content = md_path.read_text(encoding="utf-8")
        assert "# Tower Guard Report" in content


# ===========================================================================
# TestRunTowerGuard
# ===========================================================================

class TestRunTowerGuard:
    def test_returns_dict_with_required_keys(self):
        result = cat_tower_guard.run_tower_guard()
        for key in ("version", "status", "checks", "generated_at", "root"):
            assert key in result, f"missing key: {key}"

    def test_status_is_pass_or_fail(self):
        result = cat_tower_guard.run_tower_guard()
        assert result["status"] in ("pass", "fail")

    def test_checks_is_list(self):
        result = cat_tower_guard.run_tower_guard()
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) >= 1

    def test_each_check_has_required_keys(self):
        result = cat_tower_guard.run_tower_guard()
        for check in result["checks"]:
            for key in ("name", "status", "ok", "issues"):
                assert key in check, f"check missing key: {key}"


# ===========================================================================
# TestMain
# ===========================================================================

class TestMain:
    def test_main_returns_zero_or_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["cat_tower_guard.py"])
        result = cat_tower_guard.main()
        assert result in (0, 1)

    def test_main_prints_status_line(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["cat_tower_guard.py"])
        cat_tower_guard.main()
        out = capsys.readouterr().out
        assert "Tower guard status:" in out

    def test_main_write_report(self, monkeypatch, tmp_path, capsys):
        """--write-report flag exercises write_reports(); patched so no real files change."""
        captured = {}

        def fake_write_reports(report, rp, jp):
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text("test", encoding="utf-8")
            jp.write_text("{}", encoding="utf-8")
            captured["called"] = True

        monkeypatch.setattr(cat_tower_guard, "write_reports", fake_write_reports)
        monkeypatch.setattr(sys, "argv", ["cat_tower_guard.py", "--write-report"])
        result = cat_tower_guard.main()
        assert result in (0, 1)
        assert captured.get("called") is True

    def test_main_no_write_report_writes_nothing(self, monkeypatch, tmp_path, capsys):
        """Without --write-report, no files should be written to the real repo."""
        calls = []

        def fake_write_reports(report, rp, jp):
            calls.append((rp, jp))

        monkeypatch.setattr(cat_tower_guard, "write_reports", fake_write_reports)
        monkeypatch.setattr(sys, "argv", ["cat_tower_guard.py"])
        result = cat_tower_guard.main()
        assert result in (0, 1)
        assert calls == [], "write_reports should not be called without --write-report"
