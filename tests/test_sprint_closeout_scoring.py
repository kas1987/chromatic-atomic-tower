"""Tests for scoring-outcome derivation in scripts/cat_sprint_closeout.py.

Covers the reviewer concern (PR #27, codex #3432967883): archived BEADs must
not be blanket-treated as failures. ``archived`` is reachable from both
``completed`` (success) and ``failed`` (failure), so the outcome is derived
from transition_history rather than the surface status.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_sprint_closeout as csc


def test_completed_status_scores_completed():
    assert csc._derive_bead_outcome('completed', {}) == 'completed'


def test_failed_status_scores_failed():
    assert csc._derive_bead_outcome('failed', {}) == 'failed'


def test_archived_from_completed_scores_completed():
    bead = {'transition_history': [
        {'to_status': 'reviewed'},
        {'to_status': 'completed'},
        {'to_status': 'archived'},
    ]}
    assert csc._derive_bead_outcome('archived', bead) == 'completed'


def test_archived_from_failed_scores_failed():
    bead = {'transition_history': [
        {'to_status': 'failed'},
        {'to_status': 'archived'},
    ]}
    assert csc._derive_bead_outcome('archived', bead) == 'failed'


def test_archived_without_history_scores_failed():
    # No evidence it ever reached completed -> conservative failure.
    assert csc._derive_bead_outcome('archived', {}) == 'failed'


def test_archived_with_malformed_history_does_not_raise():
    bead = {'transition_history': ['not-a-dict', None, {'to_status': 'completed'}]}
    assert csc._derive_bead_outcome('archived', bead) == 'completed'


def test_non_terminal_status_returns_none():
    assert csc._derive_bead_outcome('in_progress', {}) is None
    assert csc._derive_bead_outcome('blocked', {}) is None


# --- role pre-flight validation (codex #3433013374) -------------------------

import yaml


def _bead_tuple(tmp_path, bead_id, status, role):
    p = tmp_path / f'{bead_id}.yaml'
    body = {'bead_id': bead_id, 'status': status}
    if role is not None:
        body['agent_role'] = role
    p.write_text(yaml.safe_dump(body), encoding='utf-8')
    return (bead_id, status, p)


def test_validate_roles_accepts_known_role(tmp_path):
    beads = [_bead_tuple(tmp_path, 'B-1', 'completed', 'Builder')]
    assert csc._validate_scorecard_roles(beads) == []


def test_validate_roles_flags_unknown_role(tmp_path):
    beads = [_bead_tuple(tmp_path, 'B-1', 'completed', 'Architect')]
    errors = csc._validate_scorecard_roles(beads)
    assert errors == [('B-1', 'Architect')]


def test_validate_roles_skips_non_scoring_status(tmp_path):
    # in_progress derives no outcome -> role is irrelevant, no error even if unknown.
    beads = [_bead_tuple(tmp_path, 'B-1', 'in_progress', 'Architect')]
    assert csc._validate_scorecard_roles(beads) == []


def test_validate_roles_defaults_missing_role_to_builder(tmp_path):
    beads = [_bead_tuple(tmp_path, 'B-1', 'completed', None)]
    assert csc._validate_scorecard_roles(beads) == []


def test_real_a011_beads_have_valid_roles():
    """Regression: every A011 BEAD maps to a real scorecard role (no Architect)."""
    from cat_align_common import beads_for_mission
    beads = beads_for_mission('MP-CAT-A011-4C01', csc.ROOT)
    assert beads, 'expected A011 BEADs to be discoverable'
    assert csc._validate_scorecard_roles(beads) == []


# ---------------------------------------------------------------------------
# Additional coverage: _append_audit, _derive_bead_outcome edge cases,
# _validate_scorecard_roles with multiple BEADs, closeout_mission dry_run
# ---------------------------------------------------------------------------

import json


def test_append_audit_writes_jsonl_line(tmp_path, monkeypatch):
    """_append_audit writes a valid JSON line to transitions.jsonl."""
    monkeypatch.setattr(csc, 'ROOT', tmp_path)
    event = {
        'timestamp': '2026-01-01T00:00:00+00:00',
        'target_type': 'mission',
        'target_id': 'MP-TEST-001',
        'from_status': 'approved',
        'to_status': 'closed',
        'allowed': True,
        'dry_run': False,
        'reason': 'test audit append',
        'evidence': 'evidence/reports/test.md',
        'actor': 'pytest',
        'message': 'direct closeout',
        'contract_path': 'missions/archived/test.yaml',
    }
    csc._append_audit(event)

    log_file = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
    assert log_file.exists()
    lines = log_file.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed['target_id'] == 'MP-TEST-001'
    assert parsed['allowed'] is True


def test_append_audit_appends_multiple_events(tmp_path, monkeypatch):
    """Multiple _append_audit calls produce multiple JSONL lines."""
    monkeypatch.setattr(csc, 'ROOT', tmp_path)
    for i in range(3):
        csc._append_audit({
            'timestamp': '2026-01-01T00:00:00+00:00',
            'target_type': 'mission',
            'target_id': f'MP-TEST-{i:03d}',
            'from_status': 'approved',
            'to_status': 'closed',
            'allowed': True,
            'dry_run': False,
            'reason': 'multi-append test',
            'evidence': 'evidence/reports/test.md',
            'actor': 'pytest',
            'message': 'direct closeout',
            'contract_path': 'missions/archived/test.yaml',
        })

    log_file = tmp_path / 'evidence' / 'logs' / 'transitions.jsonl'
    lines = log_file.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 3
    ids = [json.loads(l)['target_id'] for l in lines]
    assert ids == ['MP-TEST-000', 'MP-TEST-001', 'MP-TEST-002']


def test_derive_bead_outcome_archived_with_empty_history():
    bead = {'transition_history': []}
    assert csc._derive_bead_outcome('archived', bead) == 'failed'


def test_derive_bead_outcome_archived_with_none_history():
    bead = {'transition_history': None}
    assert csc._derive_bead_outcome('archived', bead) == 'failed'


def test_derive_bead_outcome_unknown_status_returns_none():
    # Any non-terminal, non-completed/failed status is not scored.
    for status in ('queued', 'reviewing', 'changes_requested', 'validating'):
        assert csc._derive_bead_outcome(status, {}) is None, f"Expected None for status={status!r}"


def test_validate_roles_multiple_beads_mixed(tmp_path):
    """One valid and one invalid role: only the invalid one is reported."""
    beads = [
        _bead_tuple(tmp_path, 'B-OK', 'completed', 'Builder'),
        _bead_tuple(tmp_path, 'B-BAD', 'completed', 'Architect'),
    ]
    errors = csc._validate_scorecard_roles(beads)
    assert len(errors) == 1
    assert errors[0] == ('B-BAD', 'Architect')


def test_validate_roles_archived_bead_with_completed_history_needs_valid_role(tmp_path):
    """An archived BEAD that reached 'completed' is scorable — role must be valid."""
    p = tmp_path / 'BEAD-ARCH.yaml'
    body = {
        'bead_id': 'BEAD-ARCH',
        'status': 'archived',
        'agent_role': 'Builder',
        'transition_history': [
            {'to_status': 'completed'},
            {'to_status': 'archived'},
        ],
    }
    p.write_text(yaml.safe_dump(body), encoding='utf-8')
    errors = csc._validate_scorecard_roles([('BEAD-ARCH', 'archived', p)])
    assert errors == []


def test_closeout_mission_returns_error_for_unknown_mission():
    """closeout_mission returns 1 for a mission that does not exist."""
    code = csc.closeout_mission('MP-TOTALLY-NONEXISTENT-9999', dry_run=True, evidence='none', actor='pytest')
    assert code == 1


def test_scorecard_roles_returns_set():
    """_scorecard_roles returns a non-empty lowercase set."""
    roles = csc._scorecard_roles()
    assert isinstance(roles, set)
    assert len(roles) > 0
    # All should be lowercase
    for role in roles:
        assert role == role.lower(), f"Role {role!r} should be lowercase"
