#!/usr/bin/env python3
"""Tests for scripts/cat_tower_guard.py."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_tower_guard import (  # noqa: E402
    render_markdown,
    run_tower_guard,
    validate_report,
)


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _base_fixture(root: Path) -> Path:
    _write_yaml(root / "state/TOWER_STATE.yaml", {
        "active_mission_id": "MP-TEST-001",
        "active_bead_id": "BEAD-TEST-001",
    })

    _write_yaml(root / "missions/registry/MISSION_REGISTRY.yaml", {
        "active_mission_id": "MP-TEST-001",
        "missions": [{
            "mission_id": "MP-TEST-001",
            "current_bead_id": "BEAD-TEST-001",
            "path": "missions/active/MP-TEST-001.yaml",
        }],
    })

    _write_yaml(root / "missions/active/MP-TEST-001.yaml", {
        "mission_id": "MP-TEST-001",
    })

    _write_yaml(root / "beads/active/BEAD-TEST-001.yaml", {
        "bead_id": "BEAD-TEST-001",
        "status": "active",
    })

    allowlist_path = root / "gates/hygiene/root_allowlist.yaml"
    _write_yaml(allowlist_path, {
        "allowed_files": [],
        "allowed_dirs": ["state", "missions", "beads", "gates"],
        "ignored_entries": [".git"],
    })
    return allowlist_path


def test_tower_guard_passes_on_clean_fixture(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    report = run_tower_guard(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-004",
    )
    assert report["status"] == "pass"
    assert len(report["checks"]) == 2


def test_tower_guard_fails_on_state_drift(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    _write_yaml(tmp_path / "state/TOWER_STATE.yaml", {
        "active_mission_id": "MP-TEST-001",
        "active_bead_id": "BEAD-WRONG-999",
    })

    report = run_tower_guard(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-004",
    )
    assert report["status"] == "fail"
    state_check = next(c for c in report["checks"] if c["name"] == "state_freshness")
    assert state_check["status"] == "fail"


def test_tower_guard_fails_on_root_hygiene_issue(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    (tmp_path / "stray.tmp").write_text("noise\n", encoding="utf-8")

    report = run_tower_guard(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-004",
    )
    assert report["status"] == "fail"
    hygiene_check = next(c for c in report["checks"] if c["name"] == "branch_root_hygiene")
    assert hygiene_check["status"] == "fail"


def test_render_markdown_contains_sections(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    report = run_tower_guard(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-004",
    )
    text = render_markdown(report)
    assert "Tower Guard Report" in text
    assert "state_freshness" in text
    assert "branch_root_hygiene" in text


def test_report_validates_against_schema(tmp_path):
    allowlist_path = _base_fixture(tmp_path)
    report = run_tower_guard(
        root=tmp_path,
        allowlist_path=allowlist_path,
        branch_name="feature/cat-004-004",
    )

    schema_path = ROOT_PATH / "schemas/tower_guard_report.schema.json"
    errors = validate_report(report, schema_path)
    assert errors == []
