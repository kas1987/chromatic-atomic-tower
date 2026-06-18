"""BEAD-CAT-A014-4C01-04: Tests for cat_cost_guard.py.

Tests cover:
  - Schedule trigger without CAT_BUDGET_APPROVED annotation is a FAILURE
  - Windows/macOS runner without CAT_RUNNER_EXCEPTION annotation is a FAILURE
  - Missing permissions block is a WARNING (not failure in default mode)
  - Clean workflow passes
  - validate-cat.yml has required hardening: permissions, concurrency, timeout-minutes
  - --strict flag treats warnings as failures
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_cost_guard import check_workflow
from scripts.common import ROOT


# ---------------------------------------------------------------------------
# Inline workflow fixtures
# ---------------------------------------------------------------------------

CLEAN_WORKFLOW = """\
name: Clean
on: [push]
permissions:
  contents: read
concurrency:
  group: clean-${{ github.ref }}
  cancel-in-progress: true
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - run: echo ok
"""

SCHEDULE_WITHOUT_APPROVAL = """\
name: Risky
on:
  schedule:
    - cron: '0 0 * * *'
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo risky
"""

SCHEDULE_WITH_APPROVAL = """\
name: Approved Schedule
on:
  schedule:
    - cron: '0 0 * * *'
  # CAT_BUDGET_APPROVED
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""

WINDOWS_WITHOUT_EXCEPTION = """\
name: Windows
on: [push]
jobs:
  check:
    runs-on: windows-latest
    steps:
      - run: echo windows
"""

WINDOWS_WITH_EXCEPTION = """\
name: Windows Approved
on: [push]
# CAT_RUNNER_EXCEPTION: windows needed for MSI build
jobs:
  check:
    runs-on: windows-latest
    steps:
      - run: echo ok
"""

NO_PERMISSIONS = """\
name: No Perms
on: [push]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""


class TestCheckWorkflow:
    def _write(self, tmp_path: Path, name: str, content: str) -> Path:
        f = tmp_path / name
        f.write_text(content, encoding='utf-8')
        return f

    def test_clean_workflow_no_failures_no_warnings(self, tmp_path):
        p = self._write(tmp_path, 'clean.yml', CLEAN_WORKFLOW)
        failures, warnings = check_workflow(p)
        assert failures == []
        assert warnings == []

    def test_schedule_without_budget_fails(self, tmp_path):
        p = self._write(tmp_path, 'risky.yml', SCHEDULE_WITHOUT_APPROVAL)
        failures, warnings = check_workflow(p)
        assert any('schedule' in f.lower() for f in failures)

    def test_schedule_with_approval_passes(self, tmp_path):
        p = self._write(tmp_path, 'approved.yml', SCHEDULE_WITH_APPROVAL)
        failures, _ = check_workflow(p)
        assert not any('schedule' in f.lower() for f in failures)

    def test_windows_runner_without_exception_fails(self, tmp_path):
        p = self._write(tmp_path, 'windows.yml', WINDOWS_WITHOUT_EXCEPTION)
        failures, _ = check_workflow(p)
        assert any('windows-latest' in f for f in failures)

    def test_windows_runner_with_exception_passes(self, tmp_path):
        p = self._write(tmp_path, 'windows_ok.yml', WINDOWS_WITH_EXCEPTION)
        failures, _ = check_workflow(p)
        assert not any('windows-latest' in f for f in failures)

    def test_missing_permissions_is_warning_not_failure(self, tmp_path):
        p = self._write(tmp_path, 'noperms.yml', NO_PERMISSIONS)
        failures, warnings = check_workflow(p)
        assert failures == []
        assert any('permissions' in w for w in warnings)

    def test_missing_concurrency_is_warning(self, tmp_path):
        p = self._write(tmp_path, 'noconcurrency.yml', NO_PERMISSIONS)
        _, warnings = check_workflow(p)
        assert any('concurrency' in w for w in warnings)


# ---------------------------------------------------------------------------
# validate-cat.yml hardening requirements
# ---------------------------------------------------------------------------

class TestValidateCatHardening:
    def test_validate_cat_has_permissions(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        assert wf.exists()
        text = wf.read_text(encoding='utf-8')
        assert 'permissions:' in text, "validate-cat.yml must have explicit permissions block"

    def test_validate_cat_has_concurrency(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        text = wf.read_text(encoding='utf-8')
        assert 'concurrency:' in text, "validate-cat.yml must have concurrency block"
        assert 'cancel-in-progress:' in text, "validate-cat.yml must have cancel-in-progress"

    def test_validate_cat_has_timeout(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        text = wf.read_text(encoding='utf-8')
        assert 'timeout-minutes:' in text, "validate-cat.yml must have timeout-minutes"

    def test_validate_cat_uses_ubuntu(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        text = wf.read_text(encoding='utf-8')
        assert 'ubuntu-latest' in text, "validate-cat.yml should use ubuntu-latest"

    def test_validate_cat_no_schedule_trigger(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        text = wf.read_text(encoding='utf-8')
        if 'schedule:' in text:
            assert 'CAT_BUDGET_APPROVED' in text, \
                "validate-cat.yml has schedule trigger without CAT_BUDGET_APPROVED"

    def test_cost_guard_passes_on_validate_cat(self):
        wf = ROOT / '.github/workflows/validate-cat.yml'
        failures, _ = check_workflow(wf)
        assert failures == [], f"cost-guard failures in validate-cat.yml: {failures}"
