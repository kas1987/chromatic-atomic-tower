#!/usr/bin/env python3
"""Tests for scripts/cat_branch_hygiene.py."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_branch_hygiene import (  # noqa: E402
    check_hygiene,
    evaluate_branch_hygiene,
    find_root_hygiene_issues,
    load_root_allowlist,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _allowlist_data() -> dict:
    return {
        "allowed_files": ["README.md"],
        "allowed_dirs": ["scripts", "tests", "gates"],
        "ignored_entries": [".git", ".pytest_cache"],
    }


def _base_fixture(root: Path) -> Path:
    allowlist_path = root / "gates/hygiene/root_allowlist.yaml"
    _write_yaml(allowlist_path, _allowlist_data())
    (root / "README.md").write_text("ok\n", encoding="utf-8")
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "gates").mkdir(parents=True, exist_ok=True)
    return allowlist_path


def test_load_root_allowlist_sets(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    allowlist = load_root_allowlist(allowlist_path)
    assert "README.md" in allowlist["allowed_files"]
    assert "scripts" in allowlist["allowed_dirs"]
    assert ".git" in allowlist["ignored_entries"]


def test_root_hygiene_clean_fixture(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    allowlist = load_root_allowlist(allowlist_path)
    issues = find_root_hygiene_issues(tmp_path, allowlist)
    assert issues == []


def test_root_hygiene_dirty_fixture(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    (tmp_path / "stray.tmp").write_text("noise\n", encoding="utf-8")
    allowlist = load_root_allowlist(allowlist_path)
    issues = find_root_hygiene_issues(tmp_path, allowlist)
    assert any("stray root file: stray.tmp" in item for item in issues)


def test_branch_hygiene_clean_fixture():
    issues = evaluate_branch_hygiene("feature/cat-004-003")
    assert issues == []


def test_branch_hygiene_dirty_main_branch():
    issues = evaluate_branch_hygiene("main")
    assert any("protected" in item for item in issues)


def test_branch_hygiene_dirty_detached_head():
    issues = evaluate_branch_hygiene("HEAD")
    assert any("detached HEAD" in item for item in issues)


def test_check_hygiene_integration_clean_fixture(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    result = check_hygiene(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-003",
    )
    assert result.passed
    assert result.issues == []


def test_check_hygiene_integration_dirty_fixture(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    result = check_hygiene(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="master",
    )
    assert not result.passed
    joined = " ".join(result.issues)
    assert "protected" in joined
    assert "stray root directory: logs" in joined
