#!/usr/bin/env python3
"""Tests for cat_align_check.py and extended alignment invariants."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_align_check import build_report
from scripts.cat_state_freshness import check_alignment


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


def _idle_fixture(root: Path) -> None:
    _write(root / 'state/TOWER_STATE.yaml', {
        'version': '0.1.0', 'status': 'sprint_idle', 'active_mission_id': '',
        'active_bead_id': '', 'active_sprint': 'SPRINT-IDLE', 'go_mode': 'enabled',
        'last_updated': '2026-06-18', 'operator': 'Test', 'control_planes': {},
        'current_constraints': [], 'next_command': 'python scripts/cat_resolve_go.py',
        'sprint_goal': 'idle',
    })
    _write(root / 'missions/registry/MISSION_REGISTRY.yaml', {
        'version': '0.1.0', 'last_updated': '2026-06-18', 'active_mission_id': '',
        'selection_policy': {'priority_order': ['approved'], 'tie_breakers': []},
        'missions': [],
    })


def test_idle_state_aligned(tmp_path):
    _idle_fixture(tmp_path)
    result = check_alignment(tmp_path)
    assert result.is_aligned


def test_mission_beads_complete_drift(tmp_path):
    _write(tmp_path / 'state/TOWER_STATE.yaml', {
        'version': '0.1.0', 'status': 'sprint_active', 'active_mission_id': 'MP-TEST-001',
        'active_bead_id': '', 'active_sprint': 'SPRINT-TEST', 'go_mode': 'enabled',
        'last_updated': '2026-06-18', 'operator': 'Test', 'control_planes': {},
        'current_constraints': [], 'next_command': 'python scripts/cat_resolve_go.py',
        'sprint_goal': 'test',
    })
    _write(tmp_path / 'missions/registry/MISSION_REGISTRY.yaml', {
        'version': '0.1.0', 'active_mission_id': 'MP-TEST-001',
        'selection_policy': {'priority_order': ['approved'], 'tie_breakers': []},
        'missions': [{
            'mission_id': 'MP-TEST-001', 'title': 'T', 'level': 'M3', 'status': 'approved',
            'priority': 1, 'owner': 'Test', 'risk_level': 'low', 'reversibility': 'high',
            'autonomy_level': 'L3', 'confidence': 90, 'current_bead_id': '',
            'path': 'missions/active/MP-TEST-001.yaml', 'created': '2026-06-18',
            'last_updated': '2026-06-18',
        }],
    })
    _write(tmp_path / 'missions/active/MP-TEST-001.yaml', {
        'mission_id': 'MP-TEST-001', 'title': 'T', 'status': 'approved',
    })
    _write(tmp_path / 'beads/active/BEAD-TEST-001.yaml', {
        'bead_id': 'BEAD-TEST-001', 'mission_id': 'MP-TEST-001', 'status': 'completed',
    })
    result = check_alignment(tmp_path)
    assert not result.is_aligned
    codes = [d.code for d in result.drift]
    assert 'MISSION_BEADS_COMPLETE_MISSION_OPEN' in codes


def test_build_report_json_shape(tmp_path):
    _idle_fixture(tmp_path)
    report = build_report(tmp_path)
    assert report['status'] == 'pass'
    assert 'generated_at' in report
    assert report['drift_count'] == 0
