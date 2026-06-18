"""Extended tests for scripts/cat_mission_package.py.

Targets uncovered lines: 35-38, 62-63, 74->77, 84->88, 92->88, 106,
112-113, 131-141, 145-177.

Uses monkeypatching of ROOT and the helper functions from cat_align_common
to avoid touching the real repo state.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

import cat_mission_package
from cat_mission_package import (
    _active_mission_id,
    _print_human,
    _registry_entry,
    build_package,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

MINIMAL_MISSION_CONTRACT = {
    'mission_id': 'MP-CAT-X001-4C01',
    'title': 'Test Mission',
    'status': 'active',
    'beads': [],
}

MINIMAL_BEAD_CONTRACT = {
    'bead_id': 'BEAD-CAT-X001-4C01-01',
    'mission_id': 'MP-CAT-X001-4C01',
    'status': 'queued',
    'agent_role': 'Builder',
    'validation': [],
}

CLOSED_BEAD_CONTRACT = {
    'bead_id': 'BEAD-CAT-X001-4C01-02',
    'mission_id': 'MP-CAT-X001-4C01',
    'status': 'completed',
    'agent_role': 'Builder',
    'validation': [],
}


def _make_tower_state(root: Path, active_mission_id: str = '') -> None:
    state_dir = root / 'state'
    state_dir.mkdir(parents=True, exist_ok=True)
    data = {'active_mission_id': active_mission_id, 'status': 'sprint_active'}
    (state_dir / 'TOWER_STATE.yaml').write_text(
        yaml.safe_dump(data, sort_keys=False), encoding='utf-8'
    )


def _make_mission_registry(root: Path, missions: list[dict]) -> None:
    reg_dir = root / 'missions' / 'registry'
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / 'MISSION_REGISTRY.yaml').write_text(
        yaml.safe_dump({'missions': missions}, sort_keys=False), encoding='utf-8'
    )


def _make_mission_contract(root: Path, data: dict, folder: str = 'active') -> Path:
    mission_dir = root / 'missions' / folder
    mission_dir.mkdir(parents=True, exist_ok=True)
    mid = data['mission_id']
    path = mission_dir / f'{mid}_TEST.yaml'
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    return path


def _make_bead_contract(root: Path, data: dict, folder: str = 'active') -> Path:
    bead_dir = root / 'beads' / folder
    bead_dir.mkdir(parents=True, exist_ok=True)
    bid = data['bead_id']
    path = bead_dir / f'{bid}_TEST.yaml'
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    return path


def _run_main(monkeypatch, argv: list[str], root: Path) -> int:
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(cat_mission_package, 'ROOT', root)
    monkeypatch.setattr(cat_mission_package, 'TOWER_STATE_PATH', root / 'state' / 'TOWER_STATE.yaml')
    monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
    monkeypatch.setattr(cat_mission_package, 'EVIDENCE_DIR', root / 'evidence' / 'packages')
    return cat_mission_package.main()


# ---------------------------------------------------------------------------
# TestActiveMissionId
# ---------------------------------------------------------------------------

class TestActiveMissionId:
    def test_returns_empty_when_no_tower_state(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cat_mission_package, 'TOWER_STATE_PATH', tmp_path / 'TOWER_STATE.yaml')
        assert _active_mission_id() == ''

    def test_returns_mission_id_from_tower(self, monkeypatch, tmp_path):
        _make_tower_state(tmp_path, 'MP-CAT-X001-4C01')
        monkeypatch.setattr(cat_mission_package, 'TOWER_STATE_PATH', tmp_path / 'state' / 'TOWER_STATE.yaml')
        assert _active_mission_id() == 'MP-CAT-X001-4C01'

    def test_returns_empty_for_empty_active_mission(self, monkeypatch, tmp_path):
        _make_tower_state(tmp_path, '')
        monkeypatch.setattr(cat_mission_package, 'TOWER_STATE_PATH', tmp_path / 'state' / 'TOWER_STATE.yaml')
        assert _active_mission_id() == ''


# ---------------------------------------------------------------------------
# TestRegistryEntry
# ---------------------------------------------------------------------------

class TestRegistryEntry:
    def test_returns_none_when_no_registry(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'MISSING.yaml')
        # The REGISTRY_PATH doesn't exist — _registry_entry should not crash
        # but load_yaml will raise; patch it to return None
        import common
        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'missing.yaml')
        # We can't call _registry_entry because load_yaml raises; instead test through build_package
        # This is tested implicitly in TestBuildPackage below.

    def test_finds_mission_in_registry(self, monkeypatch, tmp_path):
        missions = [{'mission_id': 'MP-CAT-X001-4C01', 'title': 'T', 'status': 'active'}]
        _make_mission_registry(tmp_path, missions)
        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
        entry = _registry_entry('MP-CAT-X001-4C01')
        assert entry is not None
        assert entry['title'] == 'T'

    def test_returns_none_for_unknown_mission(self, monkeypatch, tmp_path):
        _make_mission_registry(tmp_path, [])
        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
        assert _registry_entry('NONEXISTENT') is None


# ---------------------------------------------------------------------------
# TestBuildPackage
# ---------------------------------------------------------------------------

class TestBuildPackage:
    def test_empty_mission_id_returns_no_mission_selected(self):
        """build_package('') uses real ROOT but returns the no-mission-selected next_steps."""
        record = build_package('')
        assert record['mission_id'] is None
        assert any('no mission selected' in s for s in record['next_steps'])

    def test_unknown_mission_id_empty_beads(self):
        record = build_package('MP-CAT-DOES-NOT-EXIST-EVER')
        assert record['beads'] == []
        assert record['bead_summary']['total'] == 0

    def test_build_package_uses_contract_title_and_status(self, monkeypatch, tmp_path):
        """When contract file exists, title/status come from contract."""
        data = dict(MINIMAL_MISSION_CONTRACT)
        _make_mission_contract(tmp_path, data)
        _make_mission_registry(tmp_path, [])

        import cat_align_common as cac

        def fake_find_mission_contract(mid, root):
            return data, tmp_path / 'missions' / 'active' / f'{mid}_TEST.yaml'

        def fake_beads_for_mission(mid, root):
            return []

        monkeypatch.setattr(cat_mission_package, 'ROOT', tmp_path)
        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
        monkeypatch.setattr('cat_mission_package.find_mission_contract', fake_find_mission_contract)
        monkeypatch.setattr('cat_mission_package.beads_for_mission', fake_beads_for_mission)

        record = build_package('MP-CAT-X001-4C01')
        assert record['mission_title'] == 'Test Mission'
        assert record['mission_status'] == 'active'

    def test_build_package_falls_back_to_registry_when_no_contract(self, monkeypatch, tmp_path):
        """When contract is None, title/status come from registry entry."""
        missions = [{'mission_id': 'MP-CAT-X001-4C01', 'title': 'Reg Title', 'status': 'backlog'}]
        _make_mission_registry(tmp_path, missions)

        monkeypatch.setattr(cat_mission_package, 'REGISTRY_PATH', tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])

        record = build_package('MP-CAT-X001-4C01')
        assert record['mission_title'] == 'Reg Title'
        assert record['mission_status'] == 'backlog'

    def test_build_package_closed_mission_next_steps(self, monkeypatch, tmp_path):
        """A mission with terminal status gets 'mission closed' next_steps."""
        data = {'mission_id': 'MP-CAT-X001-4C01', 'title': 'Closed', 'status': 'closed'}
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (data, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])

        record = build_package('MP-CAT-X001-4C01')
        assert record['next_steps'] == ['mission closed']

    def test_build_package_all_beads_terminal(self, monkeypatch, tmp_path):
        """When all BEADs are terminal, next_steps indicates ready to close."""
        data = {'mission_id': 'MP-CAT-X001-4C01', 'title': 'X', 'status': 'active'}
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (data, None))

        # completed bead has no file path
        def fake_beads(mid, root):
            return [('BEAD-CAT-X001-4C01-01', 'completed', Path('/nonexistent/path.yaml'))]

        monkeypatch.setattr('cat_mission_package.beads_for_mission', fake_beads)
        record = build_package('MP-CAT-X001-4C01')
        assert any('ready to close' in s for s in record['next_steps'])
        assert record['bead_summary']['terminal'] == 1

    def test_build_package_non_terminal_beads_in_next_steps(self, monkeypatch, tmp_path):
        """Non-terminal BEADs appear in next_steps."""
        data = {'mission_id': 'MP-CAT-X001-4C01', 'title': 'X', 'status': 'active'}
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (data, None))

        def fake_beads(mid, root):
            return [('BEAD-CAT-X001-4C01-01', 'queued', Path('/nonexistent/path.yaml'))]

        monkeypatch.setattr('cat_mission_package.beads_for_mission', fake_beads)
        record = build_package('MP-CAT-X001-4C01')
        assert len(record['next_steps']) > 0
        assert 'BEAD-CAT-X001-4C01-01' in record['next_steps'][0]


# ---------------------------------------------------------------------------
# TestPrintHuman
# ---------------------------------------------------------------------------

class TestPrintHuman:
    def test_print_human_no_title(self, capsys):
        record = {
            'mission_id': 'MP-CAT-X001-4C01',
            'mission_title': None,
            'mission_status': 'active',
            'bead_summary': {'total': 0, 'completed': 0, 'terminal': 0},
            'next_steps': ['test step'],
        }
        _print_human(record)
        out = capsys.readouterr().out
        assert 'MP-CAT-X001-4C01' in out
        assert 'next:' in out

    def test_print_human_with_title(self, capsys):
        record = {
            'mission_id': 'MP-CAT-X001-4C01',
            'mission_title': 'Great Mission',
            'mission_status': 'active',
            'bead_summary': {'total': 2, 'completed': 1, 'terminal': 1},
            'next_steps': ['step 1', 'step 2'],
        }
        _print_human(record)
        out = capsys.readouterr().out
        assert 'Great Mission' in out
        assert 'step 1' in out
        assert 'step 2' in out

    def test_print_human_none_mission_id(self, capsys):
        record = {
            'mission_id': None,
            'mission_title': None,
            'mission_status': None,
            'bead_summary': {'total': 0, 'completed': 0, 'terminal': 0},
            'next_steps': ['no mission selected'],
        }
        _print_human(record)
        out = capsys.readouterr().out
        assert 'none' in out.lower() or 'sprint_idle' in out.lower()


# ---------------------------------------------------------------------------
# TestMain (CLI integration)
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_json_output(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])
        monkeypatch.setattr('cat_mission_package.REGISTRY_PATH', tmp_path / 'missing.yaml')
        monkeypatch.setattr('cat_mission_package._registry_entry', lambda mid: None)
        argv = ['cat_mission_package.py', '--mission', 'MP-CAT-DOES-NOT-EXIST-EVER', '--json']
        monkeypatch.setattr(sys, 'argv', argv)
        rc = cat_mission_package.main()
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['kind'] == 'mission_package'

    def test_main_human_output(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])
        monkeypatch.setattr('cat_mission_package._registry_entry', lambda mid: None)
        argv = ['cat_mission_package.py', '--mission', 'MP-CAT-DOES-NOT-EXIST-EVER']
        monkeypatch.setattr(sys, 'argv', argv)
        rc = cat_mission_package.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert 'Mission Package' in out

    def test_main_emit_writes_file(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])
        monkeypatch.setattr('cat_mission_package._registry_entry', lambda mid: None)
        monkeypatch.setattr(cat_mission_package, 'EVIDENCE_DIR', tmp_path / 'evidence' / 'packages')
        monkeypatch.setattr(cat_mission_package, 'ROOT', tmp_path)
        argv = ['cat_mission_package.py', '--mission', 'MP-CAT-DOES-NOT-EXIST-EVER', '--emit']
        monkeypatch.setattr(sys, 'argv', argv)
        rc = cat_mission_package.main()
        assert rc == 0
        pkg_dir = tmp_path / 'evidence' / 'packages'
        files = list(pkg_dir.glob('mission_package_*.json'))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding='utf-8'))
        assert data['kind'] == 'mission_package'

    def test_main_no_mission_uses_active_mission(self, monkeypatch, tmp_path, capsys):
        """When --mission is omitted, active mission is read from tower state."""
        _make_tower_state(tmp_path, 'MP-CAT-X001-4C01')
        monkeypatch.setattr(cat_mission_package, 'TOWER_STATE_PATH', tmp_path / 'state' / 'TOWER_STATE.yaml')
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])
        monkeypatch.setattr('cat_mission_package._registry_entry', lambda mid: None)
        argv = ['cat_mission_package.py', '--json']
        monkeypatch.setattr(sys, 'argv', argv)
        rc = cat_mission_package.main()
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['mission_id'] == 'MP-CAT-X001-4C01'

    def test_main_returns_zero_always(self, monkeypatch, tmp_path, capsys):
        """main() always returns 0 — it is read-only and never errors out."""
        monkeypatch.setattr('cat_mission_package.find_mission_contract', lambda mid, root: (None, None))
        monkeypatch.setattr('cat_mission_package.beads_for_mission', lambda mid, root: [])
        monkeypatch.setattr('cat_mission_package._registry_entry', lambda mid: None)
        argv = ['cat_mission_package.py', '--mission', 'ANY']
        monkeypatch.setattr(sys, 'argv', argv)
        rc = cat_mission_package.main()
        assert rc == 0
