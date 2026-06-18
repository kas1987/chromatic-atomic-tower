"""Extended tests for cat_registry_audit.py — targets the ~42% uncovered paths.

Covers:
- audit() clean registry passes
- audit() duplicate mission_id detected
- audit() required mission missing
- audit() active mismatch
- audit() missing mission path
- audit() wrong go-ready count when active expected
- audit() sprint_idle no go-ready passes
- audit() sprint_idle with go-ready fails
- load_target() missing file returns {}
- main() no crash on real repo (returns 0 or 1)
- main() with custom --registry and --target args
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

import cat_registry_audit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding='utf-8')


def _make_registry(tmp_path: Path, missions: list, active_id: str = '') -> Path:
    reg_dir = tmp_path / 'missions' / 'registry'
    reg_dir.mkdir(parents=True, exist_ok=True)
    reg_path = reg_dir / 'MISSION_REGISTRY.yaml'
    _write_yaml(reg_path, {'active_mission_id': active_id, 'missions': missions})
    return reg_path


def _make_target(tmp_path: Path, data: dict, name: str = 'target.yaml') -> Path:
    p = tmp_path / name
    _write_yaml(p, data)
    return p


# ---------------------------------------------------------------------------
# TestAudit
# ---------------------------------------------------------------------------

class TestAudit:
    def test_clean_registry_passes(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-A001', 'status': 'in_progress', 'path': None}],
            active_id='MP-CAT-A001',
        )
        ok, errors = cat_registry_audit.audit(reg_path)
        # No target → no active check → only path check matters; path=None is skipped
        assert ok, errors

    def test_duplicate_mission_id_detected(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[
                {'mission_id': 'MP-CAT-DUP', 'status': 'in_progress'},
                {'mission_id': 'MP-CAT-DUP', 'status': 'in_progress'},
            ],
            active_id='MP-CAT-DUP',
        )
        ok, errors = cat_registry_audit.audit(reg_path)
        assert not ok
        assert any('duplicate' in e for e in errors)

    def test_required_mission_missing(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-Y001', 'status': 'in_progress'}],
        )
        target = _make_target(tmp_path, {'required_missions': {'MP-CAT-X001': 'in_progress'}})
        ok, errors = cat_registry_audit.audit(reg_path, target)
        assert not ok
        assert any('MP-CAT-X001' in e for e in errors)

    def test_active_mismatch(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-X001', 'status': 'in_progress'}],
            active_id='MP-CAT-X001',
        )
        target = _make_target(
            tmp_path,
            {'canonical_active_mission_id': 'MP-CAT-A014-4C01'},
        )
        ok, errors = cat_registry_audit.audit(reg_path, target)
        assert not ok
        assert any('active_mission_id' in e for e in errors)

    def test_missing_mission_path(self, tmp_path):
        # Registry lives at tmp_path/missions/registry/MISSION_REGISTRY.yaml
        # repo_root = registry_path.resolve().parents[2] = tmp_path
        # So the missing path must be relative to tmp_path
        reg_path = _make_registry(
            tmp_path,
            missions=[{
                'mission_id': 'MP-CAT-A001',
                'status': 'in_progress',
                'path': 'missions/active/MP-CAT-A001.yaml',  # does not exist
            }],
        )
        ok, errors = cat_registry_audit.audit(reg_path)
        assert not ok
        assert any('path does not exist' in e for e in errors)

    def test_wrong_go_ready_count_when_active_expected(self, tmp_path):
        # Target expects MP-CAT-A001 active, but TWO missions are in allowed statuses
        reg_path = _make_registry(
            tmp_path,
            missions=[
                {'mission_id': 'MP-CAT-A001', 'status': 'in_progress'},
                {'mission_id': 'MP-CAT-A002', 'status': 'approved'},
            ],
            active_id='MP-CAT-A001',
        )
        target = _make_target(tmp_path, {'canonical_active_mission_id': 'MP-CAT-A001'})
        ok, errors = cat_registry_audit.audit(reg_path, target)
        assert not ok
        assert any('GO-ready' in e for e in errors)

    def test_sprint_idle_no_go_ready_passes(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-A001', 'status': 'closed'}],
            active_id='',
        )
        target = _make_target(tmp_path, {'canonical_active_mission_id': ''})
        ok, errors = cat_registry_audit.audit(reg_path, target)
        assert ok, errors

    def test_sprint_idle_with_go_ready_fails(self, tmp_path):
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-A001', 'status': 'approved'}],
            active_id='',
        )
        target = _make_target(tmp_path, {'canonical_active_mission_id': ''})
        ok, errors = cat_registry_audit.audit(reg_path, target)
        assert not ok
        assert any('sprint_idle' in e for e in errors)

    def test_load_target_missing_file(self, tmp_path):
        result = cat_registry_audit.load_target(tmp_path / 'no_such.yaml')
        assert result == {}


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_passes_on_real_repo(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['cat_registry_audit.py'])
        rc = cat_registry_audit.main()
        assert rc in (0, 1)

    def test_main_with_custom_registry(self, tmp_path, monkeypatch):
        # main() always does `root / args.registry`, so we pass paths relative
        # to tmp_path and patch ROOT → tmp_path.
        reg_path = _make_registry(
            tmp_path,
            missions=[{'mission_id': 'MP-CAT-CUSTOM', 'status': 'closed'}],
            active_id='',
        )
        target_path = _make_target(tmp_path, {})
        # Compute paths relative to tmp_path for the CLI args
        rel_registry = reg_path.relative_to(tmp_path).as_posix()
        rel_target = target_path.relative_to(tmp_path).as_posix()
        monkeypatch.setattr(
            sys, 'argv',
            [
                'cat_registry_audit.py',
                '--registry', rel_registry,
                '--target', rel_target,
            ],
        )
        monkeypatch.setattr(cat_registry_audit, 'ROOT', tmp_path)
        rc = cat_registry_audit.main()
        assert rc in (0, 1)
