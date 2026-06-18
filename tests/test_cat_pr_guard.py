"""BEAD-CAT-A014-4C01-05: Tests for cat_pr_guard.py.

Tests cover:
  - Valid PR body passes (has Mission ID, BEAD ID, evidence path)
  - Missing Mission ID is rejected
  - Missing BEAD ID is rejected
  - Missing evidence path is rejected
  - Non-standard Mission ID format is rejected
  - check_templates passes when all templates exist
  - --check-samples exits 0
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_pr_guard import check_pr_body, check_templates


VALID_BODY = """\
## Mission

Mission ID: MP-CAT-A014-4C01

## BEAD

BEAD ID: BEAD-CAT-A014-4C01-05

## Evidence

Evidence path: evidence/reports/pr-guard-pytest-output.txt
"""


class TestCheckPrBody:
    def test_valid_body_no_errors(self):
        assert check_pr_body(VALID_BODY) == []

    def test_missing_mission_id_fails(self):
        body = VALID_BODY.replace("Mission ID: MP-CAT-A014-4C01", "Mission ID:")
        errors = check_pr_body(body)
        assert any("Mission ID" in e for e in errors)

    def test_missing_bead_id_fails(self):
        body = VALID_BODY.replace("BEAD ID: BEAD-CAT-A014-4C01-05", "BEAD ID:")
        errors = check_pr_body(body)
        assert any("BEAD ID" in e for e in errors)

    def test_missing_evidence_fails(self):
        body = VALID_BODY.replace("evidence/reports/pr-guard-pytest-output.txt", "n/a")
        errors = check_pr_body(body)
        assert any("evidence" in e for e in errors)

    def test_invalid_mission_id_format(self):
        body = VALID_BODY.replace("MP-CAT-A014-4C01", "MP-WRONG-001")
        errors = check_pr_body(body)
        assert any("Mission ID" in e for e in errors)

    def test_invalid_bead_id_format(self):
        body = VALID_BODY.replace("BEAD-CAT-A014-4C01-05", "BEAD-WRONG-001")
        errors = check_pr_body(body)
        assert any("BEAD ID" in e for e in errors)

    def test_empty_body_has_all_errors(self):
        errors = check_pr_body("")
        assert any("Mission ID" in e for e in errors)
        assert any("BEAD ID" in e for e in errors)
        assert any("evidence" in e for e in errors)


class TestCheckTemplates:
    def test_templates_exist(self):
        missing = check_templates()
        assert missing == [], f"Missing templates: {missing}"


class TestCheckSamplesCli:
    def test_check_samples_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(ROOT_PATH / 'scripts' / 'cat_pr_guard.py'), '--check-samples'],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
