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
