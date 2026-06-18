"""Tests for guard evaluation and state machine logic in cat_transition.py.

Covers _transition_allowed_with_rule, _status_list, _terminal_statuses,
evaluate_guard, gate_approver_agent, update_registry_current_bead, and
maybe_move_contract — all previously untested.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

import scripts.cat_transition as cat_transition
from scripts.cat_transition import (
    _status_list,
    _terminal_statuses,
    _transition_allowed_with_rule,
    evaluate_guard,
    gate_approver_agent,
    maybe_move_contract,
    update_registry_current_bead,
)


# ---------------------------------------------------------------------------
# Shared in-memory rule fixtures (no file I/O)
# ---------------------------------------------------------------------------

_ARC_RULES: dict[str, Any] = {
    'mission_terminal_states': ['abandoned', 'learned'],
    'mission_transitions': [
        {'from': 'draft',      'to': 'triaged',    'guard': 'none',                   'reversible': False},
        {'from': 'triaged',    'to': 'approved',   'guard': 'human_gate_if_required', 'reversible': False},
        {'from': 'approved',   'to': 'dispatched', 'guard': 'active_bead_present',    'reversible': False},
        {'from': 'approved',   'to': 'blocked',    'guard': 'none',                   'reversible': False},
        {'from': 'blocked',    'to': 'approved',   'guard': 'human_gate_if_required', 'reversible': True},
        {'from': 'blocked',    'to': 'abandoned',  'guard': 'none',                   'reversible': False},
        {'from': 'in_progress','to': 'validating', 'guard': 'evidence_present',       'reversible': False},
        {'from': 'in_progress','to': 'learned',    'guard': 'closeout_complete',       'reversible': False},
    ],
    'bead_terminal_states': ['archived'],
    'bead_transitions': [
        {'from': 'queued',   'to': 'active',      'guard': 'none',              'reversible': False},
        {'from': 'active',   'to': 'in_progress', 'guard': 'none',              'reversible': False},
        {'from': 'active',   'to': 'blocked',     'guard': 'none',              'reversible': False},
        {'from': 'blocked',  'to': 'active',      'guard': 'none',              'reversible': True},
        {'from': 'queued',   'to': 'archived',    'guard': 'closeout_complete',  'reversible': False},
    ],
}

# Legacy map-style rules (mirrors shape of STATE_TRANSITION_RULES.yaml)
_MAP_RULES: dict[str, Any] = {
    'mission': {
        'statuses': ['draft', 'approved', 'closed', 'learned'],
        'terminal_statuses': ['learned'],
        'allowed_transitions': {
            'draft': ['approved'],
            'approved': ['closed'],
            'closed': ['learned'],
            'learned': [],
        },
        'evidence_required_targets': ['closed', 'learned'],
    },
    'bead': {
        'statuses': ['queued', 'active', 'completed', 'archived'],
        'terminal_statuses': ['archived'],
        'allowed_transitions': {
            'queued': ['active'],
            'active': ['completed'],
            'completed': ['archived'],
            'archived': [],
        },
        'evidence_required_targets': ['completed'],
    },
}


# ===========================================================================
# _status_list
# ===========================================================================

class TestStatusList:

    def test_arc_format_collects_from_and_to_states(self):
        statuses = _status_list(_ARC_RULES, 'mission')
        assert {'draft', 'triaged', 'approved', 'dispatched', 'blocked'}.issubset(statuses)

    def test_arc_format_bead(self):
        statuses = _status_list(_ARC_RULES, 'bead')
        assert {'queued', 'active', 'in_progress', 'blocked', 'archived'}.issubset(statuses)

    def test_map_format_returns_statuses_key(self):
        assert _status_list(_MAP_RULES, 'mission') == {'draft', 'approved', 'closed', 'learned'}

    def test_map_format_bead(self):
        assert _status_list(_MAP_RULES, 'bead') == {'queued', 'active', 'completed', 'archived'}

    def test_unknown_type_arc_format_returns_empty(self):
        assert _status_list(_ARC_RULES, 'sprint') == set()

    def test_unknown_type_map_format_returns_empty(self):
        assert _status_list(_MAP_RULES, 'sprint') == set()


# ===========================================================================
# _terminal_statuses
# ===========================================================================

class TestTerminalStatuses:

    def test_arc_format_mission(self):
        assert _terminal_statuses(_ARC_RULES, 'mission') == {'abandoned', 'learned'}

    def test_arc_format_bead(self):
        assert _terminal_statuses(_ARC_RULES, 'bead') == {'archived'}

    def test_map_format_mission(self):
        assert _terminal_statuses(_MAP_RULES, 'mission') == {'learned'}

    def test_map_format_bead(self):
        assert _terminal_statuses(_MAP_RULES, 'bead') == {'archived'}

    def test_unknown_type_returns_empty(self):
        assert _terminal_statuses(_ARC_RULES, 'sprint') == set()


# ===========================================================================
# _transition_allowed_with_rule
# ===========================================================================

class TestTransitionAllowedWithRule:

    def test_unknown_target_type_rejected(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'sprint', 'draft', 'triaged')
        assert allowed is False
        assert 'unknown target type' in msg

    def test_unknown_from_status_rejected(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'nonexistent', 'triaged')
        assert allowed is False
        assert 'unknown current status' in msg

    def test_unknown_to_status_rejected(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'draft', 'nonexistent')
        assert allowed is False
        assert 'unknown target status' in msg

    def test_valid_arc_allowed(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'draft', 'triaged')
        assert allowed is True
        assert msg == 'transition allowed'

    def test_valid_arc_returns_guard_name(self):
        _, _, rule = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'approved', 'dispatched')
        assert rule['guard'] == 'active_bead_present'

    def test_valid_arc_returns_reversible_false_for_forward(self):
        _, _, rule = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'draft', 'triaged')
        assert rule['reversible'] is False

    def test_valid_arc_returns_reversible_true_for_loop_back(self):
        _, _, rule = _transition_allowed_with_rule(_ARC_RULES, 'bead', 'blocked', 'active')
        assert rule['reversible'] is True

    def test_terminal_status_blocks_any_transition(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'abandoned', 'draft')
        assert allowed is False
        assert 'terminal' in msg

    def test_terminal_status_learned_blocked(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'learned', 'triaged')
        assert allowed is False
        assert 'terminal' in msg

    def test_terminal_bead_archived_blocked(self):
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'bead', 'archived', 'active')
        assert allowed is False
        assert 'terminal' in msg

    def test_non_terminal_no_arc_rejected(self):
        # approved → triaged has no arc defined
        allowed, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'approved', 'triaged')
        assert allowed is False
        assert 'not allowed' in msg

    def test_map_style_valid_arc_allowed(self):
        allowed, _, _ = _transition_allowed_with_rule(_MAP_RULES, 'mission', 'draft', 'approved')
        assert allowed is True

    def test_map_style_terminal_blocks(self):
        allowed, msg, _ = _transition_allowed_with_rule(_MAP_RULES, 'mission', 'learned', 'draft')
        assert allowed is False
        assert 'terminal' in msg

    def test_map_style_no_arc_rejected(self):
        allowed, msg, _ = _transition_allowed_with_rule(_MAP_RULES, 'mission', 'approved', 'draft')
        assert allowed is False

    def test_bead_arc_list_valid(self):
        allowed, _, rule = _transition_allowed_with_rule(_ARC_RULES, 'bead', 'queued', 'active')
        assert allowed is True
        assert rule['guard'] == 'none'

    def test_both_types_independent(self):
        # 'active' is a valid bead state but not a mission state in _ARC_RULES
        allowed_mission, msg, _ = _transition_allowed_with_rule(_ARC_RULES, 'mission', 'active', 'blocked')
        assert allowed_mission is False
        assert 'unknown current status' in msg

        allowed_bead, _, _ = _transition_allowed_with_rule(_ARC_RULES, 'bead', 'active', 'blocked')
        assert allowed_bead is True


# ===========================================================================
# evaluate_guard — requires a temporary file-system root
# ===========================================================================

@pytest.fixture()
def guarded_root(tmp_path, monkeypatch):
    """Minimal CAT root for guard evaluation with agent registry and rules file."""
    (tmp_path / 'agents' / 'registry').mkdir(parents=True)
    (tmp_path / 'missions' / 'registry').mkdir(parents=True)
    (tmp_path / 'beads' / 'active').mkdir(parents=True)
    (tmp_path / 'beads' / 'completed').mkdir(parents=True)
    (tmp_path / 'beads' / 'failed').mkdir(parents=True)
    (tmp_path / 'gates' / 'state').mkdir(parents=True)

    agent_reg = {
        'agents': [
            {'role': 'Auditor',      'agent_id': 'AGT-001'},
            {'role': 'Builder',      'agent_id': 'AGT-002'},
            {'role': 'Orchestrator', 'agent_id': 'AGT-003'},
        ]
    }
    (tmp_path / 'agents' / 'registry' / 'AGENT_REGISTRY.yaml').write_text(
        yaml.safe_dump(agent_reg, sort_keys=False), encoding='utf-8'
    )

    rules_yaml = {
        'gate_approver_agent': 'Auditor',
        'mission_transitions': [],
        'bead_transitions': [],
    }
    rules_path = tmp_path / 'gates' / 'state' / 'transition_rules.yaml'
    rules_path.write_text(yaml.safe_dump(rules_yaml, sort_keys=False), encoding='utf-8')

    monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
    monkeypatch.setattr(
        cat_transition, 'REGISTRY_PATH',
        tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml',
    )
    monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])
    return tmp_path


class TestEvaluateGuard:

    def test_none_guard_always_passes(self, guarded_root):
        allowed, msg = evaluate_guard('none', 'mission', {})
        assert allowed is True
        assert 'no precondition' in msg

    def test_none_guard_passes_for_bead(self, guarded_root):
        allowed, msg = evaluate_guard('none', 'bead', {})
        assert allowed is True

    def test_deferred_guards_pass(self, guarded_root):
        deferred = [
            'validation_passed', 'review_gate_pass', 'escalation_ack',
            'closeout_complete', 'rollback_plan_present', 'evidence_present',
        ]
        for guard in deferred:
            allowed, msg = evaluate_guard(guard, 'mission', {})
            assert allowed is True, f'{guard!r} should defer to True'
            assert 'deferred' in msg, f'{guard!r} message should mention deferred'

    def test_unknown_guard_defers(self, guarded_root):
        allowed, msg = evaluate_guard('some_future_guard', 'mission', {})
        assert allowed is True
        assert 'deferred' in msg

    # --- active_bead_present ---

    def test_active_bead_present_wrong_type_defers(self, guarded_root):
        allowed, msg = evaluate_guard('active_bead_present', 'bead', {})
        assert allowed is True
        assert 'deferred' in msg

    def test_active_bead_present_no_registry_fails(self, guarded_root):
        # REGISTRY_PATH does not exist → no missions in registry → False
        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is False
        assert 'no current_bead_id' in msg

    def test_active_bead_present_mission_not_in_registry_fails(self, guarded_root):
        registry = {'missions': [{'mission_id': 'MP-OTHER', 'current_bead_id': 'BEAD-001'}]}
        reg_path = guarded_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        reg_path.write_text(yaml.safe_dump(registry), encoding='utf-8')

        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is False
        assert 'no current_bead_id' in msg

    def test_active_bead_present_null_bead_id_fails(self, guarded_root):
        registry = {'missions': [{'mission_id': 'MP-TEST-001', 'current_bead_id': None}]}
        reg_path = guarded_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        reg_path.write_text(yaml.safe_dump(registry), encoding='utf-8')

        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is False
        assert 'no current_bead_id' in msg

    def test_active_bead_present_bead_missing_on_disk_fails(self, guarded_root):
        registry = {'missions': [{'mission_id': 'MP-TEST-001', 'current_bead_id': 'BEAD-TEST-001'}]}
        reg_path = guarded_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        reg_path.write_text(yaml.safe_dump(registry), encoding='utf-8')
        # No bead file created on disk

        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is False
        assert 'not found on disk' in msg

    def test_active_bead_present_bead_on_disk_passes(self, guarded_root):
        registry = {'missions': [{'mission_id': 'MP-TEST-001', 'current_bead_id': 'BEAD-TEST-001'}]}
        reg_path = guarded_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        reg_path.write_text(yaml.safe_dump(registry), encoding='utf-8')

        bead_file = guarded_root / 'beads' / 'active' / 'BEAD-TEST-001.yaml'
        bead_file.write_text(yaml.safe_dump({'bead_id': 'BEAD-TEST-001', 'status': 'active'}))

        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is True
        assert 'BEAD-TEST-001' in msg

    def test_active_bead_present_bead_in_completed_dir_passes(self, guarded_root):
        registry = {'missions': [{'mission_id': 'MP-TEST-001', 'current_bead_id': 'BEAD-DONE-001'}]}
        reg_path = guarded_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        reg_path.write_text(yaml.safe_dump(registry), encoding='utf-8')

        bead_file = guarded_root / 'beads' / 'completed' / 'BEAD-DONE-001.yaml'
        bead_file.write_text(yaml.safe_dump({'bead_id': 'BEAD-DONE-001', 'status': 'completed'}))

        allowed, msg = evaluate_guard('active_bead_present', 'mission', {'mission_id': 'MP-TEST-001'})
        assert allowed is True

    # --- human_gate_if_required ---

    def test_human_gate_not_required_passes(self, guarded_root):
        allowed, msg = evaluate_guard(
            'human_gate_if_required', 'mission',
            {'human_gate': {'required': False}},
        )
        assert allowed is True
        assert 'not required' in msg

    def test_human_gate_missing_key_treated_as_not_required(self, guarded_root):
        allowed, msg = evaluate_guard('human_gate_if_required', 'mission', {})
        assert allowed is True
        assert 'not required' in msg

    def test_human_gate_required_with_registered_approver_passes(self, guarded_root):
        # Rules file has gate_approver_agent: Auditor; agent registry has Auditor
        allowed, msg = evaluate_guard(
            'human_gate_if_required', 'mission',
            {'human_gate': {'required': True}},
        )
        assert allowed is True
        assert 'Auditor' in msg

    def test_human_gate_required_with_unregistered_approver_fails(self, guarded_root, monkeypatch):
        rules_path = guarded_root / 'gates' / 'state' / 'transition_rules.yaml'
        rules_path.write_text(
            yaml.safe_dump({'gate_approver_agent': 'UnknownRole', 'mission_transitions': []}),
            encoding='utf-8',
        )
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])

        allowed, msg = evaluate_guard(
            'human_gate_if_required', 'mission',
            {'human_gate': {'required': True}},
        )
        assert allowed is False
        assert 'not a registered role' in msg

    def test_human_gate_wrong_type_defers(self, guarded_root):
        # human_gate_if_required only handles target_type == 'mission'
        allowed, msg = evaluate_guard(
            'human_gate_if_required', 'bead',
            {'human_gate': {'required': True}},
        )
        assert allowed is True
        assert 'deferred' in msg


# ===========================================================================
# gate_approver_agent
# ===========================================================================

class TestGateApproverAgent:

    def test_no_rules_file_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [tmp_path / 'nonexistent.yaml'])
        assert gate_approver_agent() == 'Auditor'

    def test_custom_default_returned_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [tmp_path / 'nonexistent.yaml'])
        assert gate_approver_agent(default='CustomRole') == 'CustomRole'

    def test_reads_agent_from_rules(self, tmp_path, monkeypatch):
        rules_path = tmp_path / 'transition_rules.yaml'
        rules_path.write_text(yaml.safe_dump({'gate_approver_agent': 'Orchestrator'}))
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])
        assert gate_approver_agent() == 'Orchestrator'

    def test_empty_agent_falls_back_to_default(self, tmp_path, monkeypatch):
        rules_path = tmp_path / 'transition_rules.yaml'
        rules_path.write_text(yaml.safe_dump({'gate_approver_agent': ''}))
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])
        assert gate_approver_agent() == 'Auditor'

    def test_null_agent_falls_back_to_default(self, tmp_path, monkeypatch):
        rules_path = tmp_path / 'transition_rules.yaml'
        rules_path.write_text(yaml.safe_dump({'gate_approver_agent': None}))
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])
        assert gate_approver_agent() == 'Auditor'

    def test_whitespace_agent_falls_back_to_default(self, tmp_path, monkeypatch):
        rules_path = tmp_path / 'transition_rules.yaml'
        rules_path.write_text('gate_approver_agent: "   "\n')
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [rules_path])
        assert gate_approver_agent() == 'Auditor'

    def test_first_existing_rules_path_wins(self, tmp_path, monkeypatch):
        path_a = tmp_path / 'a.yaml'
        path_b = tmp_path / 'b.yaml'
        path_a.write_text(yaml.safe_dump({'gate_approver_agent': 'RoleA'}))
        path_b.write_text(yaml.safe_dump({'gate_approver_agent': 'RoleB'}))
        monkeypatch.setattr(cat_transition, 'RULES_PATHS', [path_a, path_b])
        assert gate_approver_agent() == 'RoleA'


# ===========================================================================
# update_registry_current_bead
# ===========================================================================

@pytest.fixture()
def registry_root(tmp_path, monkeypatch):
    """Isolated root with a minimal mission registry for current_bead tests."""
    (tmp_path / 'missions' / 'registry').mkdir(parents=True)
    registry = {
        'missions': [
            {
                'mission_id': 'MP-TEST-001',
                'status': 'in_progress',
                'current_bead_id': 'BEAD-OLD-001',
                'last_updated': '2026-01-01T00:00:00+00:00',
            }
        ],
        'last_updated': '2026-01-01T00:00:00+00:00',
    }
    reg_path = tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
    reg_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding='utf-8')
    monkeypatch.setattr(cat_transition, 'REGISTRY_PATH', reg_path)
    return tmp_path


def _read_registry(registry_root: Path) -> dict:
    reg_path = registry_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
    return yaml.safe_load(reg_path.read_text(encoding='utf-8'))


class TestUpdateRegistryCurrentBead:

    def test_active_status_sets_current_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-NEW-001', 'active')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == 'BEAD-NEW-001'

    def test_queued_status_sets_current_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-NEW-002', 'queued')
        # 'queued' is in the active-bead set
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == 'BEAD-NEW-002'

    def test_in_progress_status_sets_current_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-NEW-003', 'in_progress')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == 'BEAD-NEW-003'

    def test_completed_status_clears_matching_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-OLD-001', 'completed')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == ''

    def test_failed_status_clears_matching_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-OLD-001', 'failed')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == ''

    def test_archived_status_clears_matching_bead(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-OLD-001', 'archived')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == ''

    def test_completed_does_not_clear_different_bead(self, registry_root):
        # Completing a different bead should leave the registry's current_bead_id alone
        update_registry_current_bead('MP-TEST-001', 'BEAD-DIFFERENT', 'completed')
        assert _read_registry(registry_root)['missions'][0]['current_bead_id'] == 'BEAD-OLD-001'

    def test_unknown_mission_id_leaves_registry_unchanged(self, registry_root):
        reg_path = registry_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        before = reg_path.read_text(encoding='utf-8')
        update_registry_current_bead('MP-NONEXISTENT', 'BEAD-NEW', 'active')
        assert reg_path.read_text(encoding='utf-8') == before

    def test_empty_mission_id_is_noop(self, registry_root):
        reg_path = registry_root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        before = reg_path.read_text(encoding='utf-8')
        update_registry_current_bead('', 'BEAD-NEW', 'active')
        assert reg_path.read_text(encoding='utf-8') == before

    def test_registry_last_updated_is_refreshed(self, registry_root):
        update_registry_current_bead('MP-TEST-001', 'BEAD-NEW', 'active')
        data = _read_registry(registry_root)
        assert data['last_updated'] != '2026-01-01T00:00:00+00:00'


# ===========================================================================
# maybe_move_contract
# ===========================================================================

class TestMaybeMoveContract:

    def _make_contract(self, parent: Path, name: str = 'contract.yaml') -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        p = parent / name
        p.write_text('status: active\n')
        return p

    # --- mission terminal statuses ---

    def test_mission_closed_moves_to_archived(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-001.yaml')
        dest = maybe_move_contract(src, 'mission', 'closed')
        assert dest == tmp_path / 'missions' / 'archived' / 'MP-001.yaml'
        assert dest.exists()
        assert not src.exists()

    def test_mission_learned_moves_to_archived(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-002.yaml')
        dest = maybe_move_contract(src, 'mission', 'learned')
        assert dest.parent.name == 'archived'
        assert dest.exists()

    def test_mission_rolled_back_moves_to_archived(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-003.yaml')
        dest = maybe_move_contract(src, 'mission', 'rolled_back')
        assert dest.parent.name == 'archived'

    def test_mission_abandoned_moves_to_archived(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-004.yaml')
        dest = maybe_move_contract(src, 'mission', 'abandoned')
        assert dest.parent.name == 'archived'

    def test_mission_in_progress_no_move(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-005.yaml')
        dest = maybe_move_contract(src, 'mission', 'in_progress')
        assert dest == src
        assert src.exists()

    def test_mission_approved_no_move(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'missions' / 'active', 'MP-006.yaml')
        dest = maybe_move_contract(src, 'mission', 'approved')
        assert dest == src

    # --- bead statuses ---

    def test_bead_completed_moves_to_completed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'beads' / 'active', 'BEAD-001.yaml')
        dest = maybe_move_contract(src, 'bead', 'completed')
        assert dest == tmp_path / 'beads' / 'completed' / 'BEAD-001.yaml'
        assert dest.exists()
        assert not src.exists()

    def test_bead_failed_moves_to_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'beads' / 'active', 'BEAD-002.yaml')
        dest = maybe_move_contract(src, 'bead', 'failed')
        assert dest == tmp_path / 'beads' / 'failed' / 'BEAD-002.yaml'
        assert dest.exists()

    def test_bead_archived_moves_to_failed_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'beads' / 'active', 'BEAD-003.yaml')
        dest = maybe_move_contract(src, 'bead', 'archived')
        assert dest.parent.name == 'failed'
        assert dest.exists()

    def test_bead_in_progress_no_move(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'beads' / 'active', 'BEAD-004.yaml')
        dest = maybe_move_contract(src, 'bead', 'in_progress')
        assert dest == src
        assert src.exists()

    def test_bead_queued_no_move(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        src = self._make_contract(tmp_path / 'beads' / 'active', 'BEAD-005.yaml')
        dest = maybe_move_contract(src, 'bead', 'queued')
        assert dest == src

    def test_idempotent_when_already_at_dest(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        # File already at the archived destination
        dest_dir = tmp_path / 'missions' / 'archived'
        dest_dir.mkdir(parents=True)
        src = dest_dir / 'MP-007.yaml'
        src.write_text('status: closed\n')
        dest = maybe_move_contract(src, 'mission', 'closed')
        assert dest == src
        assert dest.exists()
