#!/usr/bin/env python3
"""
test_state_freshness.py — tests for cat_state_freshness.py.

All tests run against isolated fixture directories built via tmp_path.
CAT_ROOT env var is not used here; we pass the root directly to check_freshness().
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_state_freshness import check_alignment, check_freshness


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


def _base_fixture(root: Path, *, bead_status: str = 'active') -> None:
    """Write a minimal, fully-aligned fixture tree under root."""
    _write(root / 'state/TOWER_STATE.yaml', {
        'version': '0.1.0',
        'state_id': 'TOWER-STATE-TEST',
        'status': 'sprint_test_active',
        'active_sprint': 'SPRINT-TEST',
        'active_mission_id': 'MP-TEST-001',
        'active_bead_id': 'BEAD-TEST-001',
        'go_mode': 'enabled',
        'last_updated': '2026-06-17',
        'operator': 'Test',
        'control_planes': {},
        'current_constraints': [],
        'next_command': 'python scripts/cat_resolve_go.py',
        'sprint_goal': 'test',
    })
    _write(root / 'missions/registry/MISSION_REGISTRY.yaml', {
        'version': '0.1.0',
        'last_updated': '2026-06-17',
        'active_mission_id': 'MP-TEST-001',
        'selection_policy': {'priority_order': ['approved'], 'tie_breakers': []},
        'missions': [{
            'mission_id': 'MP-TEST-001',
            'title': 'Test Mission',
            'level': 'M3',
            'status': 'approved',
            'priority': 1,
            'owner': 'Test',
            'risk_level': 'low',
            'reversibility': 'high',
            'autonomy_level': 'L3',
            'confidence': 90,
            'current_bead_id': 'BEAD-TEST-001',
            'path': 'missions/active/MP-TEST-001.yaml',
            'created': '2026-06-17',
            'last_updated': '2026-06-17',
        }],
    })
    _write(root / 'missions/active/MP-TEST-001.yaml', {
        'mission_id': 'MP-TEST-001',
        'title': 'Test Mission',
        'status': 'approved',
    })
    _write(root / 'beads/active/BEAD-TEST-001.yaml', {
        'bead_id': 'BEAD-TEST-001',
        'mission_id': 'MP-TEST-001',
        'title': 'Test BEAD',
        'status': bead_status,
    })


# ---------------------------------------------------------------------------
# Tests — passing (fresh) state
# ---------------------------------------------------------------------------

def test_fresh_state_passes(tmp_path):
    _base_fixture(tmp_path)
    result = check_freshness(tmp_path)
    assert result.is_fresh, f'Expected fresh, got drift: {result.drift}'
    assert not result.drift


def test_fresh_state_ok_messages(tmp_path):
    _base_fixture(tmp_path)
    result = check_freshness(tmp_path)
    ok_text = ' '.join(result.ok)
    assert 'MP-TEST-001' in ok_text
    assert 'BEAD-TEST-001' in ok_text


def test_report_contains_fresh_marker(tmp_path):
    _base_fixture(tmp_path)
    result = check_freshness(tmp_path)
    assert 'FRESH' in result.report()
    assert 'STALE' not in result.report()


# ---------------------------------------------------------------------------
# Tests — mission ID mismatch
# ---------------------------------------------------------------------------

def test_mission_id_mismatch_detected(tmp_path):
    _base_fixture(tmp_path)
    tower_path = tmp_path / 'state/TOWER_STATE.yaml'
    data = yaml.safe_load(tower_path.read_text())
    data['active_mission_id'] = 'MP-STALE-999'
    _write(tower_path, data)

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any('active_mission_id mismatch' in d for d in result.drift)


def test_mission_id_mismatch_shows_both_ids(tmp_path):
    _base_fixture(tmp_path)
    tower_path = tmp_path / 'state/TOWER_STATE.yaml'
    data = yaml.safe_load(tower_path.read_text())
    data['active_mission_id'] = 'MP-STALE-999'
    _write(tower_path, data)

    result = check_freshness(tmp_path)
    drift_text = ' '.join(result.drift)
    assert 'MP-STALE-999' in drift_text
    assert 'MP-TEST-001' in drift_text


# ---------------------------------------------------------------------------
# Tests — missing active mission file
# ---------------------------------------------------------------------------

def test_missing_mission_file_detected(tmp_path):
    _base_fixture(tmp_path)
    (tmp_path / 'missions/active/MP-TEST-001.yaml').unlink()

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any('active mission file missing' in d for d in result.drift)


# ---------------------------------------------------------------------------
# Tests — active BEAD ID mismatch
# ---------------------------------------------------------------------------

def test_bead_id_mismatch_detected(tmp_path):
    _base_fixture(tmp_path)
    tower_path = tmp_path / 'state/TOWER_STATE.yaml'
    data = yaml.safe_load(tower_path.read_text())
    data['active_bead_id'] = 'BEAD-WRONG-999'
    _write(tower_path, data)

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any('active_bead_id mismatch' in d for d in result.drift)


# ---------------------------------------------------------------------------
# Tests — missing active BEAD file
# ---------------------------------------------------------------------------

def test_missing_bead_file_detected(tmp_path):
    _base_fixture(tmp_path)
    (tmp_path / 'beads/active/BEAD-TEST-001.yaml').unlink()

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any('active BEAD file missing' in d for d in result.drift)


# ---------------------------------------------------------------------------
# Tests — BEAD file exists but status is stale
# ---------------------------------------------------------------------------

def test_stale_bead_status_detected(tmp_path):
    _base_fixture(tmp_path, bead_status='archived')

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any("status='archived'" in d or 'status=\'archived\'' in d or 'archived' in d
               for d in result.drift)


def test_queued_bead_status_detected(tmp_path):
    _base_fixture(tmp_path, bead_status='queued')

    result = check_freshness(tmp_path)
    assert not result.is_fresh
    assert any('queued' in d for d in result.drift)


# ---------------------------------------------------------------------------
# Tests — null/missing bead_id is tolerated
# ---------------------------------------------------------------------------

def test_null_bead_id_is_ok(tmp_path):
    _base_fixture(tmp_path)
    tower_path = tmp_path / 'state/TOWER_STATE.yaml'
    data = yaml.safe_load(tower_path.read_text())
    data['active_bead_id'] = ''
    _write(tower_path, data)

    reg_path = tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'
    reg = yaml.safe_load(reg_path.read_text())
    reg['missions'][0]['current_bead_id'] = ''
    _write(reg_path, reg)

    result = check_freshness(tmp_path)
    assert result.is_fresh


def test_sprint_idle_empty_mission_ok(tmp_path):
    _write(tmp_path / 'state/TOWER_STATE.yaml', {
        'version': '0.1.0', 'status': 'sprint_idle',
        'active_mission_id': '', 'active_bead_id': '',
    })
    _write(tmp_path / 'missions/registry/MISSION_REGISTRY.yaml', {
        'version': '0.1.0', 'active_mission_id': '', 'missions': [],
    })
    result = check_alignment(tmp_path)
    assert result.is_aligned


def test_mission_collision_detected(tmp_path):
    _base_fixture(tmp_path)
    _write(tmp_path / 'missions/backlog/MP-TEST-001-dup.yaml', {
        'mission_id': 'MP-TEST-001', 'status': 'draft',
    })
    result = check_alignment(tmp_path)
    assert not result.is_aligned
    assert any(d.code == 'MISSION_ID_COLLISION' for d in result.drift)


# ---------------------------------------------------------------------------
# Tests — report format
# ---------------------------------------------------------------------------

def test_report_stale_contains_drift_lines(tmp_path):
    _base_fixture(tmp_path, bead_status='archived')
    result = check_freshness(tmp_path)
    report = result.report()
    assert 'DRIFT' in report
    assert 'STALE' in report


def test_report_ok_lines_present_on_fresh(tmp_path):
    _base_fixture(tmp_path)
    result = check_freshness(tmp_path)
    report = result.report()
    assert 'OK' in report


# ---------------------------------------------------------------------------
# Integration — run against live repo state (must be fresh)
# ---------------------------------------------------------------------------

def test_live_repo_is_fresh():
    from scripts.common import ROOT
    result = check_freshness(ROOT)
    assert result.is_fresh, (
        f'Live repo Tower state has drift — fix before proceeding:\n'
        + '\n'.join(f'  {d}' for d in result.drift)
    )
