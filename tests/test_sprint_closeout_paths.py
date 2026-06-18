"""Tests that path fields written to MISSION_REGISTRY.yaml use forward slashes.

Regression guard for the Windows backslash bug: rel() used str(path.relative_to(ROOT))
which produces backslashes on Windows. The fix uses .as_posix() instead.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_sprint_closeout as csc


def _make_registry(mission_id: str) -> dict:
    return {
        'active_mission_id': mission_id,
        'last_updated': '2026-01-01T00:00:00Z',
        'missions': [
            {
                'mission_id': mission_id,
                'status': 'active',
                'current_bead_id': '',
                'path': f'missions/active/{mission_id}.yaml',
            }
        ],
    }


def test_registry_path_uses_forward_slashes(tmp_path):
    """Path field written to registry during closeout must not contain backslashes."""
    mission_id = 'MP-T-001'
    active_dir = tmp_path / 'missions' / 'active'
    active_dir.mkdir(parents=True)
    contract_path = active_dir / f'{mission_id}.yaml'
    contract = {
        'mission_id': mission_id,
        'status': 'active',
        'last_updated': '2026-01-01T00:00:00Z',
    }
    contract_path.write_text(yaml.safe_dump(contract), encoding='utf-8')

    registry = _make_registry(mission_id)
    captured: dict = {}

    def fake_write_yaml(path, data):
        captured[str(path)] = copy.deepcopy(data)

    registry_path = tmp_path / 'MISSION_REGISTRY.yaml'

    with patch.object(csc, 'ROOT', tmp_path), \
         patch.object(csc, 'REGISTRY_PATH', registry_path), \
         patch.object(csc, 'TOWER_STATE_PATH', tmp_path / 'NONEXISTENT.yaml'), \
         patch('cat_sprint_closeout.find_mission_contract', return_value=(contract, contract_path)), \
         patch('cat_sprint_closeout.beads_for_mission', return_value=[]), \
         patch('cat_sprint_closeout._validate_scorecard_roles', return_value=[]), \
         patch('cat_sprint_closeout._append_audit'), \
         patch('cat_sprint_closeout.load_yaml', return_value=registry), \
         patch('cat_sprint_closeout.write_yaml', side_effect=fake_write_yaml), \
         patch('subprocess.run'):
        rc = csc.closeout_mission(mission_id, dry_run=False, evidence='test', actor='test')

    assert rc == 0, 'closeout should succeed'

    reg_key = str(registry_path)
    assert reg_key in captured, 'MISSION_REGISTRY.yaml was never written'

    missions = captured[reg_key]['missions']
    entry = next(m for m in missions if m['mission_id'] == mission_id)
    path_val = entry['path']

    assert '\\' not in path_val, (
        f'registry path must use forward slashes, got {path_val!r}'
    )
    assert path_val.startswith('missions/archived/'), (
        f'registry path must point to archived location, got {path_val!r}'
    )


def test_registry_path_forward_slashes_deeply_nested(tmp_path):
    """Forward-slash guarantee holds for deeply nested archived paths."""
    mission_id = 'MP-DEEP-001'
    src = tmp_path / 'missions' / 'active' / 'sub' / f'{mission_id}.yaml'
    src.parent.mkdir(parents=True)
    contract = {'mission_id': mission_id, 'status': 'active', 'last_updated': '2026-01-01T00:00:00Z'}
    src.write_text(yaml.safe_dump(contract), encoding='utf-8')

    registry = _make_registry(mission_id)
    captured: dict = {}

    def fake_write_yaml(path, data):
        captured[str(path)] = copy.deepcopy(data)

    registry_path = tmp_path / 'MISSION_REGISTRY.yaml'

    with patch.object(csc, 'ROOT', tmp_path), \
         patch.object(csc, 'REGISTRY_PATH', registry_path), \
         patch.object(csc, 'TOWER_STATE_PATH', tmp_path / 'NONEXISTENT.yaml'), \
         patch('cat_sprint_closeout.find_mission_contract', return_value=(contract, src)), \
         patch('cat_sprint_closeout.beads_for_mission', return_value=[]), \
         patch('cat_sprint_closeout._validate_scorecard_roles', return_value=[]), \
         patch('cat_sprint_closeout._append_audit'), \
         patch('cat_sprint_closeout.load_yaml', return_value=registry), \
         patch('cat_sprint_closeout.write_yaml', side_effect=fake_write_yaml), \
         patch('subprocess.run'):
        rc = csc.closeout_mission(mission_id, dry_run=False, evidence='test', actor='test')

    assert rc == 0
    missions = captured[str(registry_path)]['missions']
    entry = next(m for m in missions if m['mission_id'] == mission_id)
    assert '\\' not in entry['path'], (
        f'path must not contain backslashes even for nested paths: {entry["path"]!r}'
    )
