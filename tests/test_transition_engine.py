from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.common import ROOT, load_json, load_yaml
from scripts.cat_transition import (
    _registry_roles,
    _status_list,
    _terminal_statuses,
    _transition_allowed_with_rule,
    _transition_rule,
    append_audit_event,
    evaluate_guard,
    evidence_required,
    transition_allowed,
)


def test_mission_transition_allowed():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'mission', 'approved', 'in_progress')
    assert allowed is True
    assert message == 'transition allowed'


def test_bead_transition_allowed():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, _ = transition_allowed(rules, 'bead', 'active', 'in_progress')
    assert allowed is True


def test_invalid_transition_denied():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'bead', 'queued', 'completed')
    assert allowed is False
    assert 'not allowed' in message


def test_terminal_transition_denied():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'mission', 'learned', 'in_progress')
    assert allowed is False
    assert 'terminal' in message


def test_evidence_required_targets():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    # Map-style rules use evidence_required_targets; from_status is ignored
    assert evidence_required(rules, 'bead', None, 'completed') is True
    assert evidence_required(rules, 'bead', None, 'in_progress') is False


def test_transition_event_schema_accepts_sample():
    schema = load_json(ROOT / 'schemas/transition_event.schema.json')
    event = {
        'timestamp': '2026-06-17T00:00:00+00:00',
        'target_type': 'bead',
        'target_id': 'BEAD-CAT-001-001',
        'from_status': 'active',
        'to_status': 'in_progress',
        'allowed': True,
        'dry_run': True,
        'reason': 'unit test sample',
        'evidence': '',
    }
    errors = list(Draft202012Validator(schema).iter_errors(event))
    assert errors == []


# ---------------------------------------------------------------------------
# Helpers: inline synthetic rules fixtures
# ---------------------------------------------------------------------------

def _arc_rules(**kwargs):
    """Build minimal arc-list style rules with mission_transitions."""
    defaults = {
        'mission_terminal_states': ['abandoned', 'learned'],
        'bead_terminal_states': ['archived'],
        'mission_transitions': [
            {'from': 'draft', 'to': 'triaged', 'guard': 'none', 'reversible': False},
            {'from': 'triaged', 'to': 'approved', 'guard': 'human_gate_if_required', 'reversible': False},
            {'from': 'approved', 'to': 'dispatched', 'guard': 'active_bead_present', 'reversible': False},
            {'from': 'dispatched', 'to': 'in_progress', 'guard': 'none', 'reversible': False},
            {'from': 'in_progress', 'to': 'validating', 'guard': 'evidence_present', 'reversible': False},
            {'from': 'validating', 'to': 'in_progress', 'guard': 'none', 'reversible': True},
            {'from': 'approved', 'to': 'blocked', 'guard': 'none', 'reversible': False},
            {'from': 'blocked', 'to': 'approved', 'guard': 'none', 'reversible': True},
            {'from': 'draft', 'to': 'abandoned', 'guard': 'none', 'reversible': False},
        ],
        'bead_transitions': [
            {'from': 'queued', 'to': 'active', 'guard': 'none', 'reversible': False},
            {'from': 'active', 'to': 'in_progress', 'guard': 'none', 'reversible': False},
            {'from': 'in_progress', 'to': 'validating', 'guard': 'evidence_present', 'reversible': False},
            {'from': 'validating', 'to': 'reviewed', 'guard': 'none', 'reversible': False},
            {'from': 'reviewed', 'to': 'completed', 'guard': 'none', 'reversible': False},
            {'from': 'completed', 'to': 'archived', 'guard': 'none', 'reversible': False},
            {'from': 'in_progress', 'to': 'failed', 'guard': 'none', 'reversible': False},
            {'from': 'failed', 'to': 'archived', 'guard': 'none', 'reversible': False},
        ],
    }
    defaults.update(kwargs)
    return defaults


def _map_rules():
    """Build legacy map-style rules (mission and bead are dicts with allowed_transitions)."""
    return {
        'mission': {
            'statuses': ['draft', 'triaged', 'approved', 'abandoned', 'learned'],
            'terminal_statuses': ['abandoned', 'learned'],
            'evidence_required_targets': ['learned'],
            'allowed_transitions': {
                'draft': ['triaged', 'abandoned'],
                'triaged': ['approved'],
                'approved': ['dispatched'],
                'abandoned': [],
                'learned': [],
            },
        },
        'bead': {
            'statuses': ['queued', 'active', 'in_progress', 'completed', 'archived'],
            'terminal_statuses': ['completed', 'archived'],
            'evidence_required_targets': ['completed'],
            'allowed_transitions': {
                'queued': ['active'],
                'active': ['in_progress'],
                'in_progress': ['completed'],
                'completed': ['archived'],
                'archived': [],
            },
        },
    }


# ---------------------------------------------------------------------------
# _status_list — arc-list vs map-style
# ---------------------------------------------------------------------------

class TestStatusList:

    def test_arc_list_collects_from_and_to(self):
        rules = _arc_rules()
        statuses = _status_list(rules, 'mission')
        assert 'draft' in statuses
        assert 'triaged' in statuses
        assert 'in_progress' in statuses
        assert 'abandoned' in statuses

    def test_map_style_returns_statuses_field(self):
        rules = _map_rules()
        statuses = _status_list(rules, 'mission')
        assert statuses == {'draft', 'triaged', 'approved', 'abandoned', 'learned'}

    def test_arc_list_bead_statuses(self):
        rules = _arc_rules()
        statuses = _status_list(rules, 'bead')
        assert 'queued' in statuses
        assert 'archived' in statuses

    def test_empty_transitions_returns_empty_set(self):
        rules = {'mission_transitions': []}
        statuses = _status_list(rules, 'mission')
        assert statuses == set()


# ---------------------------------------------------------------------------
# _terminal_statuses — arc-list vs map-style
# ---------------------------------------------------------------------------

class TestTerminalStatuses:

    def test_arc_list_terminal_states(self):
        rules = _arc_rules()
        terminals = _terminal_statuses(rules, 'mission')
        assert terminals == {'abandoned', 'learned'}

    def test_arc_list_bead_terminal_states(self):
        rules = _arc_rules()
        terminals = _terminal_statuses(rules, 'bead')
        assert terminals == {'archived'}

    def test_map_style_terminal_statuses(self):
        rules = _map_rules()
        terminals = _terminal_statuses(rules, 'mission')
        assert 'abandoned' in terminals
        assert 'learned' in terminals

    def test_empty_terminal_list(self):
        rules = {'mission_terminal_states': []}
        assert _terminal_statuses(rules, 'mission') == set()


# ---------------------------------------------------------------------------
# _transition_rule — arc-list vs map-style
# ---------------------------------------------------------------------------

class TestTransitionRule:

    def test_arc_list_found(self):
        rules = _arc_rules()
        rule = _transition_rule(rules, 'mission', 'draft', 'triaged')
        assert rule is not None
        assert rule['guard'] == 'none'
        assert rule['reversible'] is False

    def test_arc_list_reversible_flag(self):
        rules = _arc_rules()
        rule = _transition_rule(rules, 'mission', 'validating', 'in_progress')
        assert rule is not None
        assert rule['reversible'] is True

    def test_arc_list_not_found_returns_none(self):
        rules = _arc_rules()
        rule = _transition_rule(rules, 'mission', 'draft', 'learned')
        assert rule is None

    def test_map_style_found_returns_stub(self):
        rules = _map_rules()
        rule = _transition_rule(rules, 'mission', 'draft', 'triaged')
        assert rule is not None
        assert rule['guard'] == 'none'
        assert rule['reversible'] is False

    def test_map_style_not_found_returns_none(self):
        rules = _map_rules()
        rule = _transition_rule(rules, 'mission', 'draft', 'learned')
        assert rule is None

    def test_guard_with_evidence_present(self):
        rules = _arc_rules()
        rule = _transition_rule(rules, 'mission', 'in_progress', 'validating')
        assert rule is not None
        assert rule['guard'] == 'evidence_present'


# ---------------------------------------------------------------------------
# transition_allowed — unknown type / unknown status edge cases
# ---------------------------------------------------------------------------

class TestTransitionAllowedEdgeCases:

    def test_unknown_target_type_rejected(self):
        rules = _arc_rules()
        allowed, message = transition_allowed(rules, 'sprint', 'draft', 'triaged')
        assert allowed is False
        assert 'unknown target type' in message

    def test_unknown_from_status_rejected(self):
        rules = _arc_rules()
        allowed, message = transition_allowed(rules, 'mission', 'nonexistent_state', 'triaged')
        assert allowed is False
        assert 'unknown current status' in message

    def test_unknown_to_status_rejected(self):
        rules = _arc_rules()
        allowed, message = transition_allowed(rules, 'mission', 'draft', 'nonexistent_state')
        assert allowed is False
        assert 'unknown target status' in message

    def test_terminal_state_message_mentions_terminal(self):
        rules = _arc_rules()
        allowed, message = transition_allowed(rules, 'mission', 'abandoned', 'draft')
        # 'abandoned' is terminal AND 'draft' is in statuses
        assert allowed is False
        assert 'terminal' in message

    def test_valid_reversible_arc_allowed(self):
        rules = _arc_rules()
        allowed, message = transition_allowed(rules, 'mission', 'blocked', 'approved')
        assert allowed is True
        assert message == 'transition allowed'

    def test_map_style_valid_transition(self):
        rules = _map_rules()
        allowed, message = transition_allowed(rules, 'mission', 'draft', 'triaged')
        assert allowed is True

    def test_map_style_invalid_arc_denied(self):
        rules = _map_rules()
        allowed, message = transition_allowed(rules, 'mission', 'draft', 'learned')
        assert allowed is False

    def test_map_style_terminal_denied(self):
        rules = _map_rules()
        # 'learned' is in terminal_statuses; 'draft' is a valid status
        allowed, message = transition_allowed(rules, 'mission', 'learned', 'draft')
        assert allowed is False


# ---------------------------------------------------------------------------
# evidence_required — arc-list format (guard: evidence_present)
# ---------------------------------------------------------------------------

class TestEvidenceRequiredArcList:

    def test_arc_list_evidence_present_guard(self):
        rules = _arc_rules()
        assert evidence_required(rules, 'mission', 'in_progress', 'validating') is True

    def test_arc_list_no_evidence_for_non_guarded_arc(self):
        rules = _arc_rules()
        assert evidence_required(rules, 'mission', 'draft', 'triaged') is False

    def test_arc_list_bead_evidence_present(self):
        rules = _arc_rules()
        assert evidence_required(rules, 'bead', 'in_progress', 'validating') is True

    def test_arc_list_bead_no_evidence_for_active(self):
        rules = _arc_rules()
        assert evidence_required(rules, 'bead', 'queued', 'active') is False

    def test_arc_list_no_match_returns_false(self):
        rules = _arc_rules()
        # non-existent arc
        assert evidence_required(rules, 'bead', 'archived', 'active') is False

    def test_map_style_evidence_required_for_completed(self):
        rules = _map_rules()
        assert evidence_required(rules, 'bead', None, 'completed') is True

    def test_map_style_evidence_not_required_for_active(self):
        rules = _map_rules()
        assert evidence_required(rules, 'bead', None, 'active') is False


# ---------------------------------------------------------------------------
# evaluate_guard
# ---------------------------------------------------------------------------

class TestEvaluateGuard:

    def test_guard_none_always_passes(self):
        ok, msg = evaluate_guard('none', 'mission', {})
        assert ok is True
        assert 'no precondition' in msg

    def test_guard_deferred_passes(self):
        ok, msg = evaluate_guard('validation_passed', 'bead', {})
        assert ok is True
        assert 'deferred' in msg

    def test_human_gate_not_required_passes(self):
        data = {'human_gate': {'required': False}}
        ok, msg = evaluate_guard('human_gate_if_required', 'mission', data)
        assert ok is True
        assert 'not required' in msg

    def test_human_gate_required_with_registered_agent_passes(self):
        # The real AGENT_REGISTRY has 'Auditor' registered; gate_approver_agent defaults to Auditor.
        data = {'human_gate': {'required': True}}
        ok, msg = evaluate_guard('human_gate_if_required', 'mission', data)
        # Auditor is registered so this should pass.
        assert ok is True
        assert 'auditor' in msg.lower() or 'gate' in msg.lower()

    def test_active_bead_present_guard_no_mission_id(self):
        # No mission_id in data -> guard fails
        ok, msg = evaluate_guard('active_bead_present', 'mission', {})
        assert ok is False
        assert 'no current_bead_id' in msg or 'mission has no' in msg


# ---------------------------------------------------------------------------
# _registry_roles
# ---------------------------------------------------------------------------

class TestRegistryRoles:

    def test_registry_roles_contains_known_roles(self):
        roles = _registry_roles()
        # AGENT_REGISTRY has Orchestrator, Builder, Auditor, etc.
        assert 'auditor' in roles
        assert 'builder' in roles
        assert 'orchestrator' in roles

    def test_registry_roles_are_lowercase(self):
        roles = _registry_roles()
        for role in roles:
            assert role == role.lower(), f'Role {role!r} should be lowercase'

    def test_registry_roles_is_nonempty(self):
        roles = _registry_roles()
        assert len(roles) > 0


# ---------------------------------------------------------------------------
# append_audit_event
# ---------------------------------------------------------------------------

class TestAppendAuditEvent:

    def test_audit_event_appended_to_log(self, tmp_path, monkeypatch):
        import scripts.cat_transition as cat_transition
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        rules = {
            'audit': {'event_log': 'evidence/logs/transitions.jsonl'},
        }
        event = {
            'timestamp': '2026-01-01T00:00:00+00:00',
            'target_type': 'mission',
            'target_id': 'MP-TEST-001',
            'from_status': 'draft',
            'to_status': 'triaged',
            'allowed': True,
            'dry_run': True,
            'reason': 'unit test',
            'evidence': '',
        }
        append_audit_event(event, rules)
        log_path = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
        assert log_path.exists()
        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed['target_id'] == 'MP-TEST-001'

    def test_audit_event_multiple_appends(self, tmp_path, monkeypatch):
        import scripts.cat_transition as cat_transition
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        rules = {'audit': {'event_log': 'evidence/logs/transitions.jsonl'}}
        event = {
            'timestamp': '2026-01-01T00:00:00+00:00',
            'target_type': 'bead',
            'target_id': 'BEAD-001',
            'from_status': 'queued',
            'to_status': 'active',
            'allowed': True,
            'dry_run': False,
            'reason': 'first',
            'evidence': '',
        }
        append_audit_event(event, rules)
        event2 = dict(event, reason='second', to_status='in_progress')
        append_audit_event(event2, rules)
        log_path = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
        lines = log_path.read_text(encoding='utf-8').strip().splitlines()
        assert len(lines) == 2

    def test_audit_event_uses_default_log_path(self, tmp_path, monkeypatch):
        import scripts.cat_transition as cat_transition
        monkeypatch.setattr(cat_transition, 'ROOT', tmp_path)
        # Rules without an audit key should fall back gracefully
        rules = {}
        event = {
            'timestamp': '2026-01-01T00:00:00+00:00',
            'target_type': 'mission',
            'target_id': 'MP-X',
            'from_status': 'draft',
            'to_status': 'triaged',
            'allowed': True,
            'dry_run': True,
            'reason': 'default path test',
            'evidence': '',
        }
        append_audit_event(event, rules)
        # Default path is evidence/logs/transitions.jsonl
        log_path = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
        assert log_path.exists()


# ---------------------------------------------------------------------------
# _transition_allowed_with_rule — guard and reversible metadata
# ---------------------------------------------------------------------------

class TestTransitionAllowedWithRule:

    def test_returns_rule_metadata_on_success(self):
        rules = _arc_rules()
        allowed, message, rule = _transition_allowed_with_rule(rules, 'mission', 'draft', 'triaged')
        assert allowed is True
        assert rule['guard'] == 'none'
        assert rule['reversible'] is False

    def test_reversible_true_on_rework_arc(self):
        rules = _arc_rules()
        allowed, message, rule = _transition_allowed_with_rule(rules, 'mission', 'validating', 'in_progress')
        assert allowed is True
        assert rule['reversible'] is True

    def test_unknown_type_returns_guard_none(self):
        rules = _arc_rules()
        allowed, message, rule = _transition_allowed_with_rule(rules, 'sprint', 'a', 'b')
        assert allowed is False
        assert rule['guard'] == 'none'

    def test_terminal_from_state_includes_terminal_in_message(self):
        rules = _arc_rules()
        # 'abandoned' is terminal; 'draft' exists in statuses
        allowed, message, rule = _transition_allowed_with_rule(rules, 'mission', 'abandoned', 'draft')
        assert allowed is False
        assert 'terminal' in message


# ---------------------------------------------------------------------------
# Real transition_rules.yaml — arc-list format
# ---------------------------------------------------------------------------

class TestArcListRulesFile:

    def test_mission_happy_path_arcs_allowed(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        happy_path = [
            ('draft', 'triaged'),
            ('triaged', 'approved'),
            ('dispatched', 'in_progress'),
        ]
        for from_s, to_s in happy_path:
            allowed, msg = transition_allowed(rules, 'mission', from_s, to_s)
            assert allowed is True, f'{from_s}->{to_s}: {msg}'

    def test_bead_happy_path_arcs_allowed(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        happy_path = [
            ('queued', 'active'),
            ('active', 'in_progress'),
            ('validating', 'reviewed'),
            ('reviewed', 'completed'),
        ]
        for from_s, to_s in happy_path:
            allowed, msg = transition_allowed(rules, 'bead', from_s, to_s)
            assert allowed is True, f'{from_s}->{to_s}: {msg}'

    def test_arc_list_terminal_states_mission(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        terminals = _terminal_statuses(rules, 'mission')
        assert 'abandoned' in terminals
        assert 'learned' in terminals

    def test_arc_list_terminal_states_bead(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        terminals = _terminal_statuses(rules, 'bead')
        assert 'archived' in terminals

    def test_arc_list_evidence_required_for_in_progress_to_validating_bead(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        assert evidence_required(rules, 'bead', 'in_progress', 'validating') is True

    def test_arc_list_evidence_not_required_for_queued_to_active(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        assert evidence_required(rules, 'bead', 'queued', 'active') is False

    def test_bead_blocking_arc_allowed(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        allowed, _ = transition_allowed(rules, 'bead', 'in_progress', 'blocked')
        assert allowed is True

    def test_bead_unblocking_arc_allowed(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        allowed, _ = transition_allowed(rules, 'bead', 'blocked', 'active')
        assert allowed is True

    def test_bead_archived_is_terminal(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        allowed, message = transition_allowed(rules, 'bead', 'archived', 'queued')
        assert allowed is False
        assert 'terminal' in message

    def test_mission_abandoned_is_terminal(self):
        rules = load_yaml(ROOT / 'gates/state/transition_rules.yaml')
        allowed, message = transition_allowed(rules, 'mission', 'abandoned', 'draft')
        assert allowed is False
        assert 'terminal' in message


# ---------------------------------------------------------------------------
# Legacy STATE_TRANSITION_RULES.yaml — map-style format
# ---------------------------------------------------------------------------

class TestMapStyleRulesFile:

    def test_map_style_mission_valid_arc(self):
        rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
        allowed, _ = transition_allowed(rules, 'mission', 'draft', 'triaged')
        assert allowed is True

    def test_map_style_mission_terminal_state(self):
        rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
        allowed, message = transition_allowed(rules, 'mission', 'learned', 'approved')
        assert allowed is False
        assert 'terminal' in message

    def test_map_style_bead_terminal_archived(self):
        rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
        allowed, message = transition_allowed(rules, 'bead', 'archived', 'active')
        assert allowed is False
        assert 'terminal' in message

    def test_map_style_evidence_required_validating(self):
        rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
        assert evidence_required(rules, 'mission', None, 'validating') is True

    def test_map_style_evidence_not_required_dispatched(self):
        rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
        assert evidence_required(rules, 'mission', None, 'dispatched') is False
