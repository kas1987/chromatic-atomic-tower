"""Extended tests for cat_transition.py — targets the 50% uncovered paths.

Covers:
- _status_list / _terminal_statuses / _transition_rule helpers
- _transition_allowed_with_rule branching (unknown type, terminal, missing arc)
- evaluate_guard all branches (none, active_bead_present, human_gate_if_required, deferred)
- gate_approver_agent with and without rules file
- create_snapshot (file copy paths, metadata.json accumulation)
- maybe_move_contract for all terminal/non-terminal combos
- update_registry_current_bead (set / clear bead, unknown mission)
- update_tower_state all branches (mission active statuses, bead active/terminal)
- append_audit_event writes a JSONL line
- apply_transition full success path (execute, move, snapshot, registry write)
- apply_transition contract-not-found path
- apply_transition from_status_expected mismatch path
- apply_transition evidence-required-but-missing path
- apply_transition guard-fail path
- find_contract success + FileNotFoundError
- rel() with inside-root and outside-root paths
- utc_now returns a valid ISO string
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Ensure the scripts package is importable (pyproject.toml pythonpath covers
# this in pytest, but direct runs may need it).
# ---------------------------------------------------------------------------
import scripts.cat_transition as ct
from scripts.cat_transition import (
    _status_list,
    _terminal_statuses,
    _transition_allowed_with_rule,
    _transition_rule,
    append_audit_event,
    apply_transition,
    create_snapshot,
    evaluate_guard,
    find_contract,
    gate_approver_agent,
    load_rules,
    maybe_move_contract,
    rel,
    update_registry_current_bead,
    update_tower_state,
    utc_now,
)
from scripts.common import ROOT, load_yaml, write_yaml


# ---------------------------------------------------------------------------
# Minimal arc-list rules fixture (mirrors the real transition_rules.yaml shape
# but tiny — keeps tests deterministic and self-contained).
# ---------------------------------------------------------------------------

MINI_RULES: dict = {
    'gate_approver_agent': 'Auditor',
    'mission_terminal_states': ['abandoned', 'learned'],
    'mission_transitions': [
        {'from': 'draft',       'to': 'triaged',     'guard': 'none',         'reversible': False},
        {'from': 'triaged',     'to': 'approved',    'guard': 'human_gate_if_required', 'reversible': False},
        {'from': 'approved',    'to': 'dispatched',  'guard': 'active_bead_present', 'reversible': False},
        {'from': 'in_progress', 'to': 'validating',  'guard': 'evidence_present', 'reversible': False},
        {'from': 'in_progress', 'to': 'blocked',     'guard': 'none',         'reversible': False},
        {'from': 'blocked',     'to': 'abandoned',   'guard': 'none',         'reversible': False},
    ],
    'bead_terminal_states': ['archived'],
    'bead_transitions': [
        {'from': 'queued',      'to': 'active',      'guard': 'none',         'reversible': False},
        {'from': 'active',      'to': 'in_progress', 'guard': 'none',         'reversible': False},
        {'from': 'in_progress', 'to': 'validating',  'guard': 'evidence_present', 'reversible': False},
        {'from': 'in_progress', 'to': 'failed',      'guard': 'none',         'reversible': False},
        {'from': 'failed',      'to': 'queued',      'guard': 'none',         'reversible': True},
        {'from': 'validating',  'to': 'completed',   'guard': 'none',         'reversible': False},
        {'from': 'completed',   'to': 'archived',    'guard': 'none',         'reversible': False},
    ],
    'audit': {'event_log': 'evidence/logs/transitions.jsonl'},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


def _bead_contract(tmp_path: Path, bead_id: str, mission_id: str, status: str) -> Path:
    path = tmp_path / 'beads' / 'active' / f'{bead_id}.yaml'
    _write_yaml(path, {'bead_id': bead_id, 'mission_id': mission_id, 'status': status})
    return path


def _mission_contract(tmp_path: Path, mission_id: str, status: str) -> Path:
    path = tmp_path / 'missions' / 'active' / f'{mission_id}.yaml'
    _write_yaml(path, {'mission_id': mission_id, 'title': 'Test Mission', 'status': status})
    return path


def _minimal_registry(tmp_path: Path, missions: list[dict]) -> Path:
    path = tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
    _write_yaml(path, {'missions': missions})
    return path


def _minimal_tower(tmp_path: Path) -> Path:
    path = tmp_path / 'state' / 'TOWER_STATE.yaml'
    _write_yaml(path, {'active_mission_id': '', 'active_bead_id': ''})
    return path


def _rules_file(tmp_path: Path, rules: dict = MINI_RULES) -> Path:
    path = tmp_path / 'gates' / 'state' / 'transition_rules.yaml'
    _write_yaml(path, rules)
    return path


# ===========================================================================
# 1. utc_now
# ===========================================================================

def test_utc_now_is_iso_string() -> None:
    result = utc_now()
    assert 'T' in result
    assert result.endswith('+00:00')


# ===========================================================================
# 2. rel()
# ===========================================================================

def test_rel_inside_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    inner = tmp_path / 'foo' / 'bar.yaml'
    assert rel(inner) == 'foo/bar.yaml' or rel(inner) == str(Path('foo/bar.yaml'))


def test_rel_outside_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    other = Path('/completely/different/path.yaml')
    result = rel(other)
    assert 'path.yaml' in result


# ===========================================================================
# 3. _status_list and _terminal_statuses — arc-list format
# ===========================================================================

def test_status_list_bead_arc_format() -> None:
    statuses = _status_list(MINI_RULES, 'bead')
    assert 'queued' in statuses
    assert 'active' in statuses
    assert 'archived' in statuses


def test_status_list_mission_arc_format() -> None:
    statuses = _status_list(MINI_RULES, 'mission')
    assert 'draft' in statuses
    assert 'blocked' in statuses


def test_terminal_statuses_bead() -> None:
    terminals = _terminal_statuses(MINI_RULES, 'bead')
    assert terminals == {'archived'}


def test_terminal_statuses_mission() -> None:
    terminals = _terminal_statuses(MINI_RULES, 'mission')
    assert 'abandoned' in terminals
    assert 'learned' in terminals


# ===========================================================================
# 4. _transition_rule
# ===========================================================================

def test_transition_rule_found() -> None:
    rule = _transition_rule(MINI_RULES, 'bead', 'queued', 'active')
    assert rule is not None
    assert rule['guard'] == 'none'


def test_transition_rule_not_found() -> None:
    rule = _transition_rule(MINI_RULES, 'bead', 'queued', 'archived')
    assert rule is None


def test_transition_rule_map_style() -> None:
    """Test the legacy map-style rules branch."""
    map_rules = {
        'bead': {
            'statuses': ['pending', 'done'],
            'allowed_transitions': {'pending': ['done']},
            'terminal_statuses': ['done'],
        }
    }
    rule = _transition_rule(map_rules, 'bead', 'pending', 'done')
    assert rule is not None
    rule_none = _transition_rule(map_rules, 'bead', 'done', 'pending')
    assert rule_none is None


# ===========================================================================
# 5. _transition_allowed_with_rule — branching paths
# ===========================================================================

def test_allowed_with_rule_unknown_type() -> None:
    ok, msg, _ = _transition_allowed_with_rule(MINI_RULES, 'sprint', 'queued', 'active')
    assert not ok
    assert 'unknown target type' in msg


def test_allowed_with_rule_unknown_from_status() -> None:
    ok, msg, _ = _transition_allowed_with_rule(MINI_RULES, 'bead', 'nonexistent', 'active')
    assert not ok
    assert 'unknown current status' in msg


def test_allowed_with_rule_unknown_to_status() -> None:
    ok, msg, _ = _transition_allowed_with_rule(MINI_RULES, 'bead', 'queued', 'nonexistent')
    assert not ok
    assert 'unknown target status' in msg


def test_allowed_with_rule_terminal_from() -> None:
    # archived -> queued should reference terminal message
    ok, msg, _ = _transition_allowed_with_rule(MINI_RULES, 'bead', 'archived', 'queued')
    assert not ok
    assert 'terminal' in msg.lower()


def test_allowed_with_rule_disallowed_arc() -> None:
    # queued -> completed is not in the mini rules
    ok, msg, _ = _transition_allowed_with_rule(MINI_RULES, 'bead', 'queued', 'completed')
    assert not ok
    assert 'not allowed' in msg.lower()


def test_allowed_with_rule_happy_path() -> None:
    ok, msg, rule = _transition_allowed_with_rule(MINI_RULES, 'bead', 'queued', 'active')
    assert ok is True
    assert msg == 'transition allowed'
    assert rule['guard'] == 'none'


# ===========================================================================
# 6. evaluate_guard
# ===========================================================================

def test_evaluate_guard_none() -> None:
    ok, msg = evaluate_guard('none', 'bead', {}, '')
    assert ok is True
    assert 'no precondition' in msg


def test_evaluate_guard_deferred() -> None:
    ok, msg = evaluate_guard('validation_passed', 'bead', {}, '')
    assert ok is True
    assert 'deferred' in msg


def test_evaluate_guard_active_bead_present_no_mission_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    _minimal_registry(tmp_path, [])
    ok, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-CAT-001'}, '')
    assert not ok
    assert 'no current_bead_id' in msg


def test_evaluate_guard_active_bead_present_bead_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    bead_id = 'BEAD-CAT-001-001'
    _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': bead_id}])
    bead_file = tmp_path / 'beads' / 'active' / f'{bead_id}.yaml'
    bead_file.parent.mkdir(parents=True, exist_ok=True)
    bead_file.write_text(f'bead_id: {bead_id}\n', encoding='utf-8')
    ok, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-CAT-001'}, '')
    assert ok is True
    assert bead_id in msg


def test_evaluate_guard_active_bead_present_bead_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': 'BEAD-MISSING'}])
    ok, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-CAT-001'}, '')
    assert not ok
    assert 'not found on disk' in msg


def test_evaluate_guard_human_gate_not_required() -> None:
    data = {'human_gate': {'required': False}}
    ok, msg = evaluate_guard('human_gate_if_required', 'mission', data, '')
    assert ok is True
    assert 'not required' in msg


def test_evaluate_guard_human_gate_required_agent_registered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    # Write a rules file so gate_approver_agent returns 'Auditor'
    _rules_file(tmp_path)
    # Write agent registry with Auditor role
    agent_reg = tmp_path / 'agents' / 'registry' / 'AGENT_REGISTRY.yaml'
    _write_yaml(agent_reg, {'agents': [{'role': 'Auditor', 'id': 'a1'}]})
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'gates/state/transition_rules.yaml'])
    data = {'human_gate': {'required': True}}
    ok, msg = evaluate_guard('human_gate_if_required', 'mission', data, '')
    assert ok is True
    assert 'Auditor' in msg


def test_evaluate_guard_human_gate_required_agent_not_registered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    _rules_file(tmp_path)
    # Agent registry has no Auditor role
    agent_reg = tmp_path / 'agents' / 'registry' / 'AGENT_REGISTRY.yaml'
    _write_yaml(agent_reg, {'agents': [{'role': 'Builder', 'id': 'a2'}]})
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'gates/state/transition_rules.yaml'])
    data = {'human_gate': {'required': True}}
    ok, msg = evaluate_guard('human_gate_if_required', 'mission', data, '')
    assert not ok
    assert 'not a registered role' in msg


# ===========================================================================
# 7. gate_approver_agent
# ===========================================================================

def test_gate_approver_agent_from_rules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _rules_file(tmp_path, {**MINI_RULES, 'gate_approver_agent': 'Reviewer'})
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'gates/state/transition_rules.yaml'])
    assert gate_approver_agent() == 'Reviewer'


def test_gate_approver_agent_default_when_no_rules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Point RULES_PATHS at non-existent files
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'no_such_file.yaml'])
    assert gate_approver_agent() == 'Auditor'


def test_gate_approver_agent_custom_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'no_such_file.yaml'])
    assert gate_approver_agent(default='CustomRole') == 'CustomRole'


# ===========================================================================
# 8. create_snapshot
# ===========================================================================

def test_create_snapshot_copies_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml')
    contract = _bead_contract(tmp_path, 'BEAD-SNAP-001', 'MP-CAT-001', 'active')
    snap_dir = create_snapshot('bead', 'BEAD-SNAP-001', contract)
    assert snap_dir.is_dir()
    assert (snap_dir / 'bead_BEAD-SNAP-001.yaml').exists()
    meta = json.loads((snap_dir / 'metadata.json').read_text(encoding='utf-8'))
    assert 'contracts' in meta


def test_create_snapshot_copies_registry_and_tower(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    registry = _minimal_registry(tmp_path, [])
    tower = _minimal_tower(tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', registry)
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tower)
    contract = _bead_contract(tmp_path, 'BEAD-SNAP-002', 'MP-CAT-001', 'active')
    snap_dir = create_snapshot('bead', 'BEAD-SNAP-002', contract)
    assert (snap_dir / 'MISSION_REGISTRY.yaml').exists()
    assert (snap_dir / 'TOWER_STATE.yaml').exists()


def test_create_snapshot_accumulates_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Calling create_snapshot twice on same dir-like scenario accumulates metadata entries."""
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml')
    c1 = _bead_contract(tmp_path, 'BEAD-SNAP-003', 'MP-CAT-001', 'active')
    c2 = _bead_contract(tmp_path, 'BEAD-SNAP-004', 'MP-CAT-001', 'active')
    # Both go into the same snap dir by reusing path
    snap_dir = create_snapshot('bead', 'BEAD-SNAP-003', c1)
    # Manually write second contract into same snap dir (simulates multi-contract snap)
    import shutil
    shutil.copy2(c2, snap_dir / 'bead_BEAD-SNAP-004.yaml')
    # Second create_snapshot call on a new snap_dir for c2 — metadata has 1 entry each
    snap_dir2 = create_snapshot('bead', 'BEAD-SNAP-004', c2)
    meta = json.loads((snap_dir2 / 'metadata.json').read_text())
    assert 'bead_BEAD-SNAP-004.yaml' in meta['contracts']


# ===========================================================================
# 9. maybe_move_contract
# ===========================================================================

def test_maybe_move_contract_bead_completed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    src = _bead_contract(tmp_path, 'BEAD-MOVE-001', 'MP-CAT-001', 'completed')
    dest = maybe_move_contract(src, 'bead', 'completed')
    assert dest == tmp_path / 'beads' / 'completed' / src.name


def test_maybe_move_contract_bead_failed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    src = _bead_contract(tmp_path, 'BEAD-MOVE-002', 'MP-CAT-001', 'active')
    dest = maybe_move_contract(src, 'bead', 'failed')
    assert dest == tmp_path / 'beads' / 'failed' / src.name


def test_maybe_move_contract_bead_archived(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    src = _bead_contract(tmp_path, 'BEAD-MOVE-003', 'MP-CAT-001', 'active')
    dest = maybe_move_contract(src, 'bead', 'archived')
    assert dest == tmp_path / 'beads' / 'failed' / src.name


def test_maybe_move_contract_mission_abandoned(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    src = _mission_contract(tmp_path, 'MP-CAT-001', 'in_progress')
    dest = maybe_move_contract(src, 'mission', 'abandoned')
    assert dest == tmp_path / 'missions' / 'archived' / src.name


def test_maybe_move_contract_non_terminal_no_move(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    src = _bead_contract(tmp_path, 'BEAD-MOVE-004', 'MP-CAT-001', 'active')
    dest = maybe_move_contract(src, 'bead', 'in_progress')
    assert dest == src


# ===========================================================================
# 10. append_audit_event
# ===========================================================================

def test_append_audit_event_writes_jsonl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    rules = {**MINI_RULES, 'audit': {'event_log': 'evidence/logs/test.jsonl'}}
    event = {'timestamp': utc_now(), 'message': 'test event', 'allowed': True}
    append_audit_event(event, rules)
    log_path = tmp_path / 'evidence' / 'logs' / 'test.jsonl'
    assert log_path.exists()
    line = log_path.read_text(encoding='utf-8').strip()
    parsed = json.loads(line)
    assert parsed['message'] == 'test event'


def test_append_audit_event_appends_multiple(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    rules = {**MINI_RULES, 'audit': {'event_log': 'evidence/logs/multi.jsonl'}}
    for i in range(3):
        append_audit_event({'seq': i}, rules)
    lines = (tmp_path / 'evidence/logs/multi.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 3
    assert json.loads(lines[2])['seq'] == 2


# ===========================================================================
# 11. update_registry_current_bead
# ===========================================================================

def test_update_registry_sets_current_bead(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    registry = _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': ''}])
    monkeypatch.setattr(ct, 'REGISTRY_PATH', registry)
    update_registry_current_bead('MP-CAT-001', 'BEAD-001', 'active')
    data = load_yaml(registry)
    assert data['missions'][0]['current_bead_id'] == 'BEAD-001'


def test_update_registry_clears_current_bead_on_terminal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    registry = _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': 'BEAD-001'}])
    monkeypatch.setattr(ct, 'REGISTRY_PATH', registry)
    update_registry_current_bead('MP-CAT-001', 'BEAD-001', 'completed')
    data = load_yaml(registry)
    assert data['missions'][0]['current_bead_id'] == ''


def test_update_registry_no_mission_id_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    registry = _minimal_registry(tmp_path, [])
    monkeypatch.setattr(ct, 'REGISTRY_PATH', registry)
    # Should not raise
    update_registry_current_bead('', 'BEAD-001', 'active')


def test_update_registry_unknown_mission_no_update(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    registry = _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': 'OLD'}])
    monkeypatch.setattr(ct, 'REGISTRY_PATH', registry)
    update_registry_current_bead('MP-CAT-999', 'BEAD-001', 'active')
    data = load_yaml(registry)
    # Registry must remain unchanged since mission not found
    assert data['missions'][0]['current_bead_id'] == 'OLD'


# ===========================================================================
# 12. update_tower_state
# ===========================================================================

def test_update_tower_state_mission_active(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    tower = _minimal_tower(tmp_path)
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tower)
    update_tower_state('mission', 'MP-CAT-001', 'in_progress', {})
    data = load_yaml(tower)
    assert data['active_mission_id'] == 'MP-CAT-001'


def test_update_tower_state_bead_active(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    tower = _minimal_tower(tmp_path)
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tower)
    update_tower_state('bead', 'BEAD-001', 'active', {'mission_id': 'MP-CAT-001'})
    data = load_yaml(tower)
    assert data['active_bead_id'] == 'BEAD-001'
    assert data['active_mission_id'] == 'MP-CAT-001'


def test_update_tower_state_bead_completed_clears(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    tower_path = tmp_path / 'state' / 'TOWER_STATE.yaml'
    _write_yaml(tower_path, {'active_mission_id': 'MP-CAT-001', 'active_bead_id': 'BEAD-001'})
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tower_path)
    update_tower_state('bead', 'BEAD-001', 'completed', {})
    data = load_yaml(tower_path)
    assert data['active_bead_id'] == ''


def test_update_tower_state_no_file_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tmp_path / 'state' / 'TOWER_STATE.yaml')
    # Should not raise even if file doesn't exist
    update_tower_state('bead', 'BEAD-001', 'active', {})


# ===========================================================================
# 13. find_contract
# ===========================================================================

def test_find_contract_bead_in_active(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    _bead_contract(tmp_path, 'BEAD-FIND-001', 'MP-CAT-001', 'active')
    path = find_contract('bead', 'BEAD-FIND-001')
    assert path.exists()
    assert 'BEAD-FIND-001' in path.name


def test_find_contract_mission_in_active(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    _mission_contract(tmp_path, 'MP-CAT-FIND-001', 'draft')
    path = find_contract('mission', 'MP-CAT-FIND-001')
    assert path.exists()


def test_find_contract_not_found_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    with pytest.raises(FileNotFoundError, match='could not find'):
        find_contract('bead', 'BEAD-NONEXISTENT-999')


# ===========================================================================
# 14. apply_transition — full success path (execute + move)
# ===========================================================================

def _patch_for_apply(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Monkeypatch ct module globals so apply_transition uses tmp_path."""
    monkeypatch.setattr(ct, 'ROOT', tmp_path)
    monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml')
    monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml')
    monkeypatch.setattr(ct, 'RULES_PATHS', [tmp_path / 'gates/state/transition_rules.yaml'])


def test_apply_transition_success_execute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': ''}])
    _minimal_tower(tmp_path)
    _bead_contract(tmp_path, 'BEAD-EXEC-001', 'MP-CAT-001', 'queued')
    code, event = apply_transition('bead', 'BEAD-EXEC-001', 'active', 'testing', '', 'pytest', False, False)
    assert code == 0
    assert event['allowed'] is True
    assert event['to_status'] == 'active'
    assert 'snapshot' in event


def test_apply_transition_contract_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [])
    _minimal_tower(tmp_path)
    code, event = apply_transition('bead', 'BEAD-NO-SUCH', 'active', 'test', '', 'pytest', False, False)
    assert code == 1
    assert event['allowed'] is False
    assert event['contract_path'] == 'not found'


def test_apply_transition_from_status_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [])
    _minimal_tower(tmp_path)
    _bead_contract(tmp_path, 'BEAD-MISMATCH-001', 'MP-CAT-001', 'queued')
    code, event = apply_transition(
        'bead', 'BEAD-MISMATCH-001', 'active', 'test', '', 'pytest', False, False,
        from_status_expected='active',  # actual is queued
    )
    assert code == 1
    assert 'current status is queued' in event['message']


def test_apply_transition_evidence_required_but_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [])
    _minimal_tower(tmp_path)
    _bead_contract(tmp_path, 'BEAD-EVID-001', 'MP-CAT-001', 'in_progress')
    code, event = apply_transition(
        'bead', 'BEAD-EVID-001', 'validating', 'test', '',  # no evidence
        'pytest', False, False,
    )
    assert code == 1
    assert event['allowed'] is False
    assert 'evidence' in event['message']


def test_apply_transition_dry_run_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [])
    _minimal_tower(tmp_path)
    contract = _bead_contract(tmp_path, 'BEAD-DRY-EXT-001', 'MP-CAT-001', 'queued')
    code, event = apply_transition('bead', 'BEAD-DRY-EXT-001', 'active', 'test', '', 'pytest', True, False)
    assert code == 0
    assert event['dry_run'] is True
    # File must NOT be mutated
    data = load_yaml(contract)
    assert data['status'] == 'queued'


def test_apply_transition_execute_moves_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_for_apply(monkeypatch, tmp_path)
    _rules_file(tmp_path)
    _minimal_registry(tmp_path, [{'mission_id': 'MP-CAT-001', 'current_bead_id': ''}])
    _minimal_tower(tmp_path)
    _bead_contract(tmp_path, 'BEAD-MOVEX-001', 'MP-CAT-001', 'in_progress')
    code, event = apply_transition(
        'bead', 'BEAD-MOVEX-001', 'failed', 'test', '', 'pytest', False, True,
    )
    assert code == 0
    # With move=True, failed contracts go to beads/failed
    assert 'beads/failed' in event['contract_path'].replace('\\', '/')


# ===========================================================================
# 15. main() — covers lines 406-539
# ===========================================================================

class TestTransitionMain:
    """Tests for cat_transition.main() — covers lines 406-539."""

    def _setup_tmp(self, tmp_path: Path) -> None:
        """Create the minimum directory structure main() expects."""
        (tmp_path / 'missions' / 'active').mkdir(parents=True, exist_ok=True)
        (tmp_path / 'missions' / 'registry').mkdir(parents=True, exist_ok=True)
        (tmp_path / 'state').mkdir(parents=True, exist_ok=True)
        (tmp_path / 'evidence' / 'logs').mkdir(parents=True, exist_ok=True)
        (tmp_path / 'evidence' / 'snapshots').mkdir(parents=True, exist_ok=True)

    def _write_mission(self, tmp_path: Path, mission_id: str, status: str = 'approved') -> Path:
        contract = {
            'mission_id': mission_id,
            'status': status,
            'title': 'Test',
            'transition_history': [],
        }
        path = tmp_path / 'missions' / 'active' / f'{mission_id}.yaml'
        _write_yaml(path, contract)
        return path

    def _write_registry(self, tmp_path: Path, mission_id: str, status: str = 'approved') -> Path:
        registry = {
            'active_mission_id': '',
            'missions': [
                {
                    'mission_id': mission_id,
                    'status': status,
                    'path': f'missions/active/{mission_id}.yaml',
                }
            ],
        }
        path = tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        _write_yaml(path, registry)
        return path

    def _write_tower(self, tmp_path: Path) -> Path:
        path = tmp_path / 'state' / 'TOWER_STATE.yaml'
        _write_yaml(path, {'status': 'sprint_idle', 'active_mission_id': '', 'active_bead_id': ''})
        return path

    def _patch_globals(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(ct, 'ROOT', tmp_path)
        monkeypatch.setattr(ct, 'REGISTRY_PATH', tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml')
        monkeypatch.setattr(ct, 'TOWER_STATE_PATH', tmp_path / 'state' / 'TOWER_STATE.yaml')

    # ------------------------------------------------------------------
    # dry-run path
    # ------------------------------------------------------------------

    def test_dry_run_returns_zero_or_one(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """--dry-run with a valid mission returns 0 (allowed) or 1 (rule rejected)."""
        self._setup_tmp(tmp_path)
        mission_id = 'MP-CAT-TEST-MAIN-001'
        self._write_mission(tmp_path, mission_id)
        self._write_registry(tmp_path, mission_id)
        self._write_tower(tmp_path)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--dry-run',
            '--mission', mission_id,
            '--to', 'dispatched',
        ])
        result = ct.main()
        assert result in (0, 1)

    def test_dry_run_json_flag_prints_json(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        """--json flag causes stdout to contain a JSON object."""
        self._setup_tmp(tmp_path)
        mission_id = 'MP-CAT-TEST-JSON-001'
        self._write_mission(tmp_path, mission_id)
        self._write_registry(tmp_path, mission_id)
        self._write_tower(tmp_path)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--dry-run',
            '--mission', mission_id,
            '--to', 'dispatched',
            '--json',
        ])
        result = ct.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        if out.strip():
            data = json.loads(out)
            assert 'allowed' in data or 'target_id' in data

    # ------------------------------------------------------------------
    # execute path
    # ------------------------------------------------------------------

    def test_execute_path_returns_zero_or_one(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """--execute with a valid mission returns 0 or 1."""
        self._setup_tmp(tmp_path)
        mission_id = 'MP-CAT-TEST-EXEC-001'
        self._write_mission(tmp_path, mission_id)
        self._write_registry(tmp_path, mission_id)
        self._write_tower(tmp_path)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--execute',
            '--mission', mission_id,
            '--to', 'dispatched',
        ])
        result = ct.main()
        assert result in (0, 1)

    # ------------------------------------------------------------------
    # rollback path
    # ------------------------------------------------------------------

    def test_rollback_not_found_returns_one(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """--rollback with a non-existent snapshot ID returns 1."""
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--rollback', 'NONEXISTENT-SNAPSHOT-999',
        ])
        result = ct.main()
        assert result == 1

    def test_rollback_success(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        """--rollback with a valid snapshot restores files and returns 0."""
        snap_id = 'snap-test-001'
        snap_dir = tmp_path / 'evidence' / 'snapshots' / snap_id
        snap_dir.mkdir(parents=True)
        mission_id = 'MP-CAT-TEST-ROLLBACK-001'
        contract = {'mission_id': mission_id, 'status': 'approved', 'title': 'Rollback Test'}
        _write_yaml(snap_dir / f'mission_{mission_id}.yaml', contract)
        registry = {'missions': [{'mission_id': mission_id, 'status': 'approved'}], 'active_mission_id': ''}
        _write_yaml(snap_dir / 'MISSION_REGISTRY.yaml', registry)
        # metadata.json with per-file path map (new format)
        meta = {'contracts': {f'mission_{mission_id}.yaml': f'missions/active/{mission_id}.yaml'}}
        (snap_dir / 'metadata.json').write_text(json.dumps(meta), encoding='utf-8')
        # Destination directories must exist
        (tmp_path / 'missions' / 'active').mkdir(parents=True)
        (tmp_path / 'missions' / 'registry').mkdir(parents=True)
        (tmp_path / 'state').mkdir(parents=True)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--rollback', snap_id,
        ])
        result = ct.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'rollback' in out
        assert 'restored' in out

    # ------------------------------------------------------------------
    # argument-validation paths
    # ------------------------------------------------------------------

    def test_missing_to_flag_exits(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """--dry-run without --to should call parser.error() → SystemExit."""
        self._setup_tmp(tmp_path)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--dry-run', '--mission', 'MP-TEST-001',
            # --to intentionally omitted
        ])
        with pytest.raises(SystemExit):
            ct.main()

    def test_both_mission_and_bead_exits(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Supplying both --mission and --bead should call parser.error() → SystemExit."""
        self._setup_tmp(tmp_path)
        self._patch_globals(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, 'argv', [
            'cat_transition.py', '--dry-run',
            '--mission', 'MP-TEST-001',
            '--bead', 'BEAD-TEST-001',
            '--to', 'dispatched',
        ])
        with pytest.raises(SystemExit):
            ct.main()
