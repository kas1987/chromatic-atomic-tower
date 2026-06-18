"""
tests/test_cat_check_repo.py

Verifies the repo health checker, including the stray-root-entry guard that
enforces CAT_MANIFEST.md sections 3 / 3.1 / 3.2 / 4 against the actual root.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cat_check_repo  # noqa: E402

ROOT = cat_check_repo.ROOT


def test_repo_check_passes_on_clean_root():
    assert cat_check_repo.main() == 0


def test_no_stray_root_entries_currently():
    assert cat_check_repo.find_stray_root_entries() == []


def test_stray_root_file_is_detected():
    stray = ROOT / "zz_pytest_stray_marker.md"
    stray.write_text("temporary test artifact\n", encoding="utf-8")
    try:
        flagged = cat_check_repo.find_stray_root_entries()
        assert "zz_pytest_stray_marker.md" in flagged
        assert cat_check_repo.main() == 1
    finally:
        stray.unlink(missing_ok=True)


def test_ignored_entries_are_not_flagged():
    # Cache/VCS entries are gitignored and must never be reported as stray.
    assert ".git" in cat_check_repo.IGNORED_ROOT_ENTRIES
    assert ".pytest_cache" in cat_check_repo.IGNORED_ROOT_ENTRIES


def test_allowlists_cover_required_files():
    # Every root-level required file must also be in the allowlist.
    root_required = {f for f in cat_check_repo.REQUIRED_FILES if "/" not in f}
    missing = root_required - cat_check_repo.ALLOWED_ROOT_FILES
    assert not missing, f"Required root files missing from ALLOWED_ROOT_FILES: {missing}"
