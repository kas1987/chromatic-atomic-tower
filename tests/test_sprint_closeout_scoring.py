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
