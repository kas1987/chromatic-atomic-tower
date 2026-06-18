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


def test_ignored_entries_are_not_flagged(tmp_path):
    # Behavioral: gitignored caches/secrets must never be reported as stray,
    # while a genuinely unknown entry must be. Exercises IGNORED_ROOT_ENTRIES
    # and the IGNORED_ROOT_PATTERNS globs (.env, .env.*, *.pem).
    (tmp_path / "README.md").write_text("allowed", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=1", encoding="utf-8")
    (tmp_path / ".env.local").write_text("SECRET=2", encoding="utf-8")
    (tmp_path / "app_key.pem").write_text("pem", encoding="utf-8")
    (tmp_path / ".github_app_token_cache").write_text("{}", encoding="utf-8")
    (tmp_path / "zz_unknown_stray.md").write_text("stray", encoding="utf-8")

    flagged = cat_check_repo.find_stray_root_entries(tmp_path)

    assert "zz_unknown_stray.md" in flagged
    for ignored in (".env", ".env.local", "app_key.pem", ".github_app_token_cache", "README.md"):
        assert ignored not in flagged, f"{ignored} should not be flagged as stray"


def test_allowlists_cover_required_files():
    # Every root-level required file must also be in the allowlist.
    root_required = {f for f in cat_check_repo.REQUIRED_FILES if "/" not in f}
    missing = root_required - cat_check_repo.ALLOWED_ROOT_FILES
    assert not missing, f"Required root files missing from ALLOWED_ROOT_FILES: {missing}"
