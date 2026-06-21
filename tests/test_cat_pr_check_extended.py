"""Extended coverage for cat_pr_check.py.

Covers: matches(), load_changed_files(), check_scope(), print_markdown(),
_detect_active_ids(), and main() paths not exercised by existing tests.

Import pattern: always ``import cat_pr_check`` so monkeypatching hits the
correct module namespace.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

import cat_pr_check

# ---------------------------------------------------------------------------
# Real bead used in tests that need a resolvable bead_id.
# BEAD-CAT-A014-4C01-03 is present in beads/active/ and has
# mission_id MP-CAT-A014-4C01.
# ---------------------------------------------------------------------------
REAL_BEAD_ID = "BEAD-CAT-A014-4C01-03"
REAL_MISSION_ID = "MP-CAT-A014-4C01"


# ===========================================================================
# TestMatches
# ===========================================================================

class TestMatches:
    def test_matches_exact_path(self):
        assert cat_pr_check.matches("scripts/foo.py", "scripts/foo.py") is True

    def test_matches_prefix_slash(self):
        assert cat_pr_check.matches("scripts/", "scripts/bar.py") is True

    def test_matches_glob_double_star(self):
        assert cat_pr_check.matches("secrets/**", "secrets/key.txt") is True

    def test_matches_glob_star(self):
        assert cat_pr_check.matches("*.md", "README.md") is True

    def test_no_match(self):
        assert cat_pr_check.matches("docs/", "scripts/foo.py") is False

    def test_matches_deep_prefix(self):
        assert cat_pr_check.matches("infra/prod/", "infra/prod/deploy.sh") is True


# ===========================================================================
# TestLoadChangedFiles
# ===========================================================================

class TestLoadChangedFiles:
    def test_loads_from_file(self, tmp_path):
        f = tmp_path / "changed.txt"
        f.write_text("scripts/foo.py\ndocs/bar.md\n", encoding="utf-8")
        result = cat_pr_check.load_changed_files(str(f))
        assert result == ["scripts/foo.py", "docs/bar.md"]

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("CAT_CHANGED_FILES", "scripts/foo.py,docs/bar.md")
        result = cat_pr_check.load_changed_files(None)
        assert result == ["scripts/foo.py", "docs/bar.md"]

    def test_returns_empty_no_env_no_file(self, monkeypatch):
        monkeypatch.delenv("CAT_CHANGED_FILES", raising=False)
        result = cat_pr_check.load_changed_files(None)
        assert result == []

    def test_skips_comment_lines_in_file(self, tmp_path):
        f = tmp_path / "changed.txt"
        f.write_text("# comment\nscripts/foo.py\n", encoding="utf-8")
        result = cat_pr_check.load_changed_files(str(f))
        assert result == ["scripts/foo.py"]


# ===========================================================================
# TestCheckScope
# ===========================================================================

class TestCheckScope:
    def test_missing_mission_id(self):
        result = cat_pr_check.check_scope("", REAL_BEAD_ID, [])
        assert result["status"] == "failed"
        assert any("missing mission id" in f for f in result["failures"])

    def test_missing_bead_id(self):
        # When bead_id is empty, load_bead returns (None, None) so
        # check_scope returns early with 'unknown bead'.
        result = cat_pr_check.check_scope(REAL_MISSION_ID, "", [])
        assert result["status"] == "failed"

    def test_unknown_bead(self):
        result = cat_pr_check.check_scope(REAL_MISSION_ID, "BEAD-DOES-NOT-EXIST-000", [])
        assert result["status"] == "failed"
        assert any("unknown bead" in f for f in result["failures"])

    def test_known_bead_passes_with_allowed_path(self):
        # BEAD-CAT-A014-4C01-03 allows evidence/manifest.yaml
        result = cat_pr_check.check_scope(
            REAL_MISSION_ID,
            REAL_BEAD_ID,
            ["evidence/manifest.yaml"],
        )
        assert result["status"] == "passed"
        assert result["failures"] == []

    def test_known_bead_fails_with_forbidden_path(self):
        result = cat_pr_check.check_scope(
            REAL_MISSION_ID,
            REAL_BEAD_ID,
            ["secrets/key.txt"],
        )
        assert result["status"] == "failed"
        assert any("forbidden" in f for f in result["failures"])


# ===========================================================================
# TestPrintMarkdown
# ===========================================================================

class TestPrintMarkdown:
    def _base_result(self, failures=None):
        return {
            "status": "passed" if not failures else "failed",
            "mission_id": REAL_MISSION_ID,
            "bead_id": REAL_BEAD_ID,
            "changed_files": ["scripts/foo.py"],
            "failures": failures or [],
        }

    def test_prints_header_and_status(self, capsys):
        cat_pr_check.print_markdown(self._base_result())
        out = capsys.readouterr().out
        assert "# CAT PR Scope Check" in out
        assert "Status:" in out

    def test_prints_failures_section_when_present(self, capsys):
        result = self._base_result(failures=["outside allowed paths: scripts/foo.py"])
        cat_pr_check.print_markdown(result)
        out = capsys.readouterr().out
        assert "## Failures" in out

    def test_no_failures_section_when_clean(self, capsys):
        cat_pr_check.print_markdown(self._base_result())
        out = capsys.readouterr().out
        assert "## Failures" not in out


# ===========================================================================
# TestDetectActiveIds
# ===========================================================================

class TestDetectActiveIds:
    def test_reads_tower_state(self):
        mission_id, bead_id = cat_pr_check._detect_active_ids()
        # Both values should be strings (may be empty if no active bead).
        assert isinstance(mission_id, str)
        assert isinstance(bead_id, str)

    def test_returns_empty_when_no_tower(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cat_pr_check, "ROOT", tmp_path)
        mission_id, bead_id = cat_pr_check._detect_active_ids()
        assert mission_id == ""
        assert bead_id == ""


# ===========================================================================
# TestMain
# ===========================================================================

class TestMain:
    def test_main_no_mission_no_bead_no_tower_skips(self, monkeypatch, tmp_path, capsys):
        """When no ids are supplied and no TOWER_STATE exists, main skips."""
        monkeypatch.setattr(cat_pr_check, "ROOT", tmp_path)
        monkeypatch.delenv("CAT_MISSION", raising=False)
        monkeypatch.delenv("CAT_BEAD", raising=False)
        monkeypatch.delenv("CAT_CHANGED_FILES", raising=False)
        monkeypatch.setattr(sys, "argv", ["cat_pr_check.py"])
        result = cat_pr_check.main()
        assert result == 0
        err = capsys.readouterr().err
        assert "skipping" in err.lower()

    def test_main_json_output(self, monkeypatch, capsys):
        """Running with a real bead + --json should not crash and produce JSON."""
        monkeypatch.delenv("CAT_MISSION", raising=False)
        monkeypatch.delenv("CAT_BEAD", raising=False)
        monkeypatch.delenv("CAT_CHANGED_FILES", raising=False)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_pr_check.py",
                "--mission", REAL_MISSION_ID,
                "--bead", REAL_BEAD_ID,
                "--json",
            ],
        )
        result = cat_pr_check.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "status" in parsed

    def test_main_explicit_missing_bead(self, monkeypatch, capsys):
        """Passing a non-existent bead id explicitly should return 1."""
        monkeypatch.delenv("CAT_MISSION", raising=False)
        monkeypatch.delenv("CAT_BEAD", raising=False)
        monkeypatch.setattr(sys, "argv", ["cat_pr_check.py", "--bead", "NONEXISTENT-BEAD-000"])
        result = cat_pr_check.main()
        assert result == 1

    def test_main_changed_files_from_env(self, monkeypatch, tmp_path, capsys):
        """CAT_CHANGED_FILES env var flows through main() correctly."""
        monkeypatch.setenv("CAT_CHANGED_FILES", "evidence/manifest.yaml")
        monkeypatch.delenv("CAT_MISSION", raising=False)
        monkeypatch.delenv("CAT_BEAD", raising=False)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_pr_check.py",
                "--mission", REAL_MISSION_ID,
                "--bead", REAL_BEAD_ID,
                "--json",
            ],
        )
        result = cat_pr_check.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "evidence/manifest.yaml" in parsed["changed_files"]
