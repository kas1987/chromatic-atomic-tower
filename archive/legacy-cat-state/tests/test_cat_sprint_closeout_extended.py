"""Extended tests for cat_sprint_closeout.py — targets the ~40% uncovered paths.

Covers:
- _append_audit() writes JSONL line, creates parent dirs
- closeout_mission() mission not found → 1
- closeout_mission() non-terminal bead → 1
- closeout_mission() already terminal → 0
- closeout_mission() dry-run → 0, registry unchanged
- _validate_scorecard_roles() no errors for known role
- main() no --dry-run/--execute → 1
- main() --dry-run with nonexistent mission → 1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

import cat_sprint_closeout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding='utf-8')


def _setup_mission(
    tmp_path: Path,
    mission_id: str = 'MP-CAT-T001',
    bead_id: str = 'BEAD-CAT-T001-01',
    bead_status: str = 'completed',
    mission_status: str = 'in_progress',
) -> tuple[str, str]:
    """Create a minimal mission/bead/registry/tower/scorecard structure."""
    # Mission contract in missions/active/
    missions_active = tmp_path / 'missions' / 'active'
    missions_active.mkdir(parents=True, exist_ok=True)
    contract = {
        'mission_id': mission_id,
        'status': mission_status,
        'title': 'Test Mission',
        'agent_role': 'Builder',
    }
    _write_yaml(missions_active / f'{mission_id}.yaml', contract)

    # Registry
    registry_dir = tmp_path / 'missions' / 'registry'
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry = {
        'active_mission_id': mission_id,
        'missions': [{
            'mission_id': mission_id,
            'status': mission_status,
            'path': f'missions/active/{mission_id}.yaml',
        }],
    }
    _write_yaml(registry_dir / 'MISSION_REGISTRY.yaml', registry)

    # BEAD
    bead_folder = 'completed' if bead_status in ('completed', 'failed', 'archived') else 'active'
    beads_dir = tmp_path / 'beads' / bead_folder
    beads_dir.mkdir(parents=True, exist_ok=True)
    bead = {
        'bead_id': bead_id,
        'mission_id': mission_id,
        'status': bead_status,
        'agent_role': 'Builder',
    }
    _write_yaml(beads_dir / f'{bead_id}.yaml', bead)

    # Tower state
    state_dir = tmp_path / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    tower = {
        'status': 'active',
        'active_mission_id': mission_id,
        'active_bead_id': bead_id,
    }
    _write_yaml(state_dir / 'TOWER_STATE.yaml', tower)

    # Scorecard
    agents_dir = tmp_path / 'agents' / 'registry'
    agents_dir.mkdir(parents=True, exist_ok=True)
    scorecard = {
        'schema_version': '0.1.0',
        'score_policy': {
            'starting_score': 70,
            'promote_threshold': 85,
            'demote_threshold': 55,
        },
        'agents': [{
            'role': 'Builder',
            'score': 70,
            'current_trust': 'provisional',
            'history': [],
        }],
    }
    _write_yaml(agents_dir / 'AGENT_SCORECARD.yaml', scorecard)

    # Log dir
    (tmp_path / 'evidence' / 'logs').mkdir(parents=True, exist_ok=True)

    # Archived dir (destination for closed contracts)
    (tmp_path / 'missions' / 'archived').mkdir(parents=True, exist_ok=True)

    return mission_id, bead_id


def _patch_root(monkeypatch, tmp_path: Path) -> None:
    """Patch ROOT everywhere it's used in cat_sprint_closeout."""
    monkeypatch.setattr(cat_sprint_closeout, 'ROOT', tmp_path)
    # The module-level constants REGISTRY_PATH and TOWER_STATE_PATH were bound
    # at import time using the original ROOT; patch them explicitly.
    monkeypatch.setattr(
        cat_sprint_closeout, 'REGISTRY_PATH',
        tmp_path / 'missions/registry/MISSION_REGISTRY.yaml',
    )
    monkeypatch.setattr(
        cat_sprint_closeout, 'TOWER_STATE_PATH',
        tmp_path / 'state/TOWER_STATE.yaml',
    )
    # Also patch common.ROOT so helpers like find_mission_contract use tmp_path
    import common
    monkeypatch.setattr(common, 'ROOT', tmp_path)
    import cat_align_common
    monkeypatch.setattr(cat_align_common, 'ROOT', tmp_path)


# ---------------------------------------------------------------------------
# TestAppendAudit
# ---------------------------------------------------------------------------

class TestAppendAudit:
    def test_appends_json_line(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_sprint_closeout, 'ROOT', tmp_path)
        log_path = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cat_sprint_closeout._append_audit({'timestamp': 'ts', 'type': 'test'})

        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed['type'] == 'test'
        assert parsed['timestamp'] == 'ts'

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_sprint_closeout, 'ROOT', tmp_path)
        # Do NOT pre-create evidence/logs — _append_audit must create them
        cat_sprint_closeout._append_audit({'x': 1})
        log_path = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
        assert log_path.exists()


# ---------------------------------------------------------------------------
# TestCloseoutMission
# ---------------------------------------------------------------------------

class TestCloseoutMission:
    def test_mission_not_found_returns_one(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        # No mission files created — should return 1
        rc = cat_sprint_closeout.closeout_mission(
            'MP-CAT-NONEXISTENT', dry_run=True, evidence='', actor='Test'
        )
        assert rc == 1

    def test_non_terminal_bead_returns_one(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        mission_id, _ = _setup_mission(tmp_path, bead_status='active')
        rc = cat_sprint_closeout.closeout_mission(
            mission_id, dry_run=True, evidence='', actor='Test'
        )
        assert rc == 1

    def test_already_terminal_returns_zero(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        mission_id, _ = _setup_mission(tmp_path, mission_status='closed')
        rc = cat_sprint_closeout.closeout_mission(
            mission_id, dry_run=True, evidence='', actor='Test'
        )
        assert rc == 0

    def test_dry_run_returns_zero(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        mission_id, _ = _setup_mission(tmp_path)
        # Prevent subprocess call from failing the test
        monkeypatch.setattr(
            cat_sprint_closeout, '_score_beads_on_closeout', lambda *a, **kw: None
        )
        rc = cat_sprint_closeout.closeout_mission(
            mission_id, dry_run=True, evidence='', actor='Test'
        )
        assert rc == 0

    def test_dry_run_doesnt_mutate_registry(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        mission_id, _ = _setup_mission(tmp_path)
        monkeypatch.setattr(
            cat_sprint_closeout, '_score_beads_on_closeout', lambda *a, **kw: None
        )
        cat_sprint_closeout.closeout_mission(
            mission_id, dry_run=True, evidence='', actor='Test'
        )
        # Registry file must be unchanged — status still 'in_progress'
        registry_path = tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'
        reg = yaml.safe_load(registry_path.read_text())
        assert reg['missions'][0]['status'] == 'in_progress'


# ---------------------------------------------------------------------------
# TestValidateScorecard
# ---------------------------------------------------------------------------

class TestValidateScorecard:
    def test_no_errors_for_known_role(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        _setup_mission(tmp_path)
        # Build a bead tuple matching the 'Builder' role in the scorecard
        bead_path = tmp_path / 'beads/completed/BEAD-CAT-T001-01.yaml'
        mission_beads = [('BEAD-CAT-T001-01', 'completed', bead_path)]
        errors = cat_sprint_closeout._validate_scorecard_roles(mission_beads)
        assert errors == []

    def test_error_for_unknown_role(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        _setup_mission(tmp_path)
        # Write a bead with an unknown role
        bead_path = tmp_path / 'beads/completed/BEAD-UNKNOWN.yaml'
        _write_yaml(bead_path, {
            'bead_id': 'BEAD-UNKNOWN',
            'status': 'completed',
            'agent_role': 'Architect',  # not in scorecard
        })
        mission_beads = [('BEAD-UNKNOWN', 'completed', bead_path)]
        errors = cat_sprint_closeout._validate_scorecard_roles(mission_beads)
        assert len(errors) == 1
        assert errors[0][1] == 'Architect'


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_no_mode_flag_returns_one(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            sys, 'argv',
            ['cat_sprint_closeout.py', '--mission', 'MP-TEST-001'],
        )
        rc = cat_sprint_closeout.main()
        assert rc == 1

    def test_main_dry_run_nonexistent_mission(self, tmp_path, monkeypatch):
        _patch_root(monkeypatch, tmp_path)
        monkeypatch.setattr(
            sys, 'argv',
            ['cat_sprint_closeout.py', '--mission', 'MP-TEST-NONEXISTENT', '--dry-run'],
        )
        rc = cat_sprint_closeout.main()
        assert rc == 1
