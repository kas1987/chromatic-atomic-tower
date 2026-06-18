"""Tests for scripts/cat_resolve_go.py — mission/BEAD selection algorithms.

Covers:
- Mission selection with priority tiebreakers
- BEAD selection algorithms
- Confidence band calculation
- Blocking logic
- Dispatch packet assembly
- Edge cases
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_resolve_go as crg


# ---------------------------------------------------------------------------
# confidence_band
# ---------------------------------------------------------------------------

def test_confidence_band_very_high():
    assert crg.confidence_band(90) == 'very_high'
    assert crg.confidence_band(100) == 'very_high'
    assert crg.confidence_band(95) == 'very_high'


def test_confidence_band_high():
    assert crg.confidence_band(75) == 'high'
    assert crg.confidence_band(89) == 'high'
    assert crg.confidence_band(80) == 'high'


def test_confidence_band_medium():
    assert crg.confidence_band(60) == 'medium'
    assert crg.confidence_band(74) == 'medium'
    assert crg.confidence_band(65) == 'medium'


def test_confidence_band_low():
    assert crg.confidence_band(40) == 'low'
    assert crg.confidence_band(59) == 'low'
    assert crg.confidence_band(50) == 'low'


def test_confidence_band_blocked():
    assert crg.confidence_band(39) == 'blocked'
    assert crg.confidence_band(0) == 'blocked'
    assert crg.confidence_band(1) == 'blocked'


# ---------------------------------------------------------------------------
# select_mission
# ---------------------------------------------------------------------------

def test_select_mission_returns_none_for_empty_registry():
    registry = {'missions': []}
    assert crg.select_mission(registry) is None


def test_select_mission_returns_none_when_no_allowed_statuses():
    registry = {'missions': [
        {'mission_id': 'MP-TEST-001', 'status': 'closed', 'priority': 1},
        {'mission_id': 'MP-TEST-002', 'status': 'abandoned', 'priority': 2},
    ]}
    assert crg.select_mission(registry) is None


def test_select_mission_returns_none_for_missing_missions_key():
    assert crg.select_mission({}) is None


def test_select_mission_picks_highest_priority_approved():
    registry = {'missions': [
        {'mission_id': 'MP-TEST-001', 'status': 'approved', 'priority': 3, 'confidence': 80, 'risk_level': 'low'},
        {'mission_id': 'MP-TEST-002', 'status': 'approved', 'priority': 1, 'confidence': 80, 'risk_level': 'low'},
        {'mission_id': 'MP-TEST-003', 'status': 'approved', 'priority': 2, 'confidence': 80, 'risk_level': 'low'},
    ]}
    result = crg.select_mission(registry)
    assert result['mission_id'] == 'MP-TEST-002'


def test_select_mission_tiebreaker_higher_confidence_wins():
    registry = {'missions': [
        {'mission_id': 'MP-LOW-CONF', 'status': 'approved', 'priority': 1, 'confidence': 60, 'risk_level': 'low', 'created': '2026-01-01'},
        {'mission_id': 'MP-HIGH-CONF', 'status': 'approved', 'priority': 1, 'confidence': 90, 'risk_level': 'low', 'created': '2026-01-01'},
    ]}
    result = crg.select_mission(registry)
    assert result['mission_id'] == 'MP-HIGH-CONF'


def test_select_mission_tiebreaker_lower_risk_wins():
    # Same priority and confidence — lower risk_level wins
    registry = {'missions': [
        {'mission_id': 'MP-HIGH-RISK', 'status': 'approved', 'priority': 1, 'confidence': 80, 'risk_level': 'high', 'created': '2026-01-01'},
        {'mission_id': 'MP-LOW-RISK', 'status': 'approved', 'priority': 1, 'confidence': 80, 'risk_level': 'low', 'created': '2026-01-01'},
    ]}
    result = crg.select_mission(registry)
    assert result['mission_id'] == 'MP-LOW-RISK'


def test_select_mission_tiebreaker_older_created_wins():
    # Same priority, confidence, risk — older creation date wins
    registry = {'missions': [
        {'mission_id': 'MP-NEWER', 'status': 'approved', 'priority': 1, 'confidence': 80, 'risk_level': 'low', 'created': '2026-06-01'},
        {'mission_id': 'MP-OLDER', 'status': 'approved', 'priority': 1, 'confidence': 80, 'risk_level': 'low', 'created': '2026-01-01'},
    ]}
    result = crg.select_mission(registry)
    assert result['mission_id'] == 'MP-OLDER'


def test_select_mission_accepts_all_allowed_statuses():
    for status in crg.ALLOWED_MISSION_STATUSES:
        registry = {'missions': [
            {'mission_id': 'MP-TEST', 'status': status, 'priority': 1},
        ]}
        result = crg.select_mission(registry)
        assert result is not None, f"Expected mission with status={status!r} to be selected"
        assert result['mission_id'] == 'MP-TEST'


def test_select_mission_ignores_disallowed_statuses():
    registry = {'missions': [
        {'mission_id': 'MP-CLOSED', 'status': 'closed', 'priority': 1},
        {'mission_id': 'MP-APPROVED', 'status': 'approved', 'priority': 5},
    ]}
    result = crg.select_mission(registry)
    assert result['mission_id'] == 'MP-APPROVED'


# ---------------------------------------------------------------------------
# select_bead
# ---------------------------------------------------------------------------

def test_select_bead_returns_none_for_no_candidates():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': None}
    result = crg.select_bead(mission, [], allow_queued=False)
    assert result is None


def test_select_bead_returns_none_when_no_bead_matches_mission():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': None}
    beads = [
        {'bead_id': 'BEAD-OTHER-001', 'mission_id': 'MP-OTHER', 'status': 'active'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=False)
    assert result is None


def test_select_bead_prefers_current_bead_id():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': 'BEAD-TEST-002'}
    beads = [
        {'bead_id': 'BEAD-TEST-001', 'mission_id': 'MP-TEST', 'status': 'active'},
        {'bead_id': 'BEAD-TEST-002', 'mission_id': 'MP-TEST', 'status': 'active'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=False)
    assert result['bead_id'] == 'BEAD-TEST-002'


def test_select_bead_falls_back_to_active_when_no_current():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': None}
    beads = [
        {'bead_id': 'BEAD-TEST-001', 'mission_id': 'MP-TEST', 'status': 'active'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=False)
    assert result['bead_id'] == 'BEAD-TEST-001'


def test_select_bead_does_not_return_queued_without_allow_queued():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': None}
    beads = [
        {'bead_id': 'BEAD-TEST-Q01', 'mission_id': 'MP-TEST', 'status': 'queued'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=False)
    assert result is None


def test_select_bead_returns_queued_when_allow_queued_and_current_set():
    """A queued BEAD is returned when it matches current_bead_id and allow_queued=True."""
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': 'BEAD-TEST-Q01'}
    beads = [
        {'bead_id': 'BEAD-TEST-Q01', 'mission_id': 'MP-TEST', 'status': 'queued'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=True)
    assert result is not None
    assert result['bead_id'] == 'BEAD-TEST-Q01'


def test_select_bead_returns_none_for_queued_only_without_current():
    """A queued BEAD without current_bead_id returns None (no active fallback for queued)."""
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': None}
    beads = [
        {'bead_id': 'BEAD-TEST-Q01', 'mission_id': 'MP-TEST', 'status': 'queued'},
    ]
    # The function falls through to `active = [b for b in candidates if b.get('status') == 'active']`
    # which is empty, so returns None even when allow_queued=True.
    result = crg.select_bead(mission, beads, allow_queued=True)
    assert result is None


def test_select_bead_current_id_not_found_falls_back_to_active():
    mission = {'mission_id': 'MP-TEST', 'current_bead_id': 'BEAD-TEST-GHOST'}
    beads = [
        {'bead_id': 'BEAD-TEST-001', 'mission_id': 'MP-TEST', 'status': 'active'},
    ]
    result = crg.select_bead(mission, beads, allow_queued=False)
    assert result['bead_id'] == 'BEAD-TEST-001'


# ---------------------------------------------------------------------------
# build_dispatch
# ---------------------------------------------------------------------------

def _make_mission(**kwargs) -> dict:
    base = {
        'mission_id': 'MP-TEST-001',
        'title': 'Test Mission',
        'level': 1,
        'risk_level': 'low',
        'path': 'missions/active/test.yaml',
    }
    base.update(kwargs)
    return base


def _make_bead(**kwargs) -> dict:
    base = {
        'bead_id': 'BEAD-TEST-001',
        'title': 'Test BEAD',
        'status': 'active',
        'agent_role': 'Builder',
        'autonomy_level': 'supervised',
        'confidence': {'current': 80, 'minimum': 60},
        'risk_level': 'low',
        'reversibility': 'reversible',
        'allowed_paths': ['src/'],
        'forbidden_paths': ['secrets/'],
        'tool_budget': {'read': 100},
        'definition_of_done': ['Tests pass'],
        'validation': [],
        'stop_conditions': ['No permission to mutate'],
        'required_output': [],
        '_path': 'beads/active/test.yaml',
    }
    base.update(kwargs)
    return base


def test_build_dispatch_ready_when_confidence_meets_minimum():
    mission = _make_mission()
    bead = _make_bead(confidence={'current': 80, 'minimum': 60})
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['dispatch_status'] == 'ready'
    assert dispatch['confidence'] == 80
    assert dispatch['confidence_minimum'] == 60
    assert dispatch['confidence_band'] == 'high'


def test_build_dispatch_blocked_when_confidence_below_minimum():
    mission = _make_mission()
    bead = _make_bead(confidence={'current': 30, 'minimum': 60})
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['dispatch_status'] == 'blocked'
    assert 'confidence below minimum' in dispatch['reason']


def test_build_dispatch_exact_minimum_is_ready():
    mission = _make_mission()
    bead = _make_bead(confidence={'current': 60, 'minimum': 60})
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['dispatch_status'] == 'ready'


def test_build_dispatch_populates_mission_fields():
    mission = _make_mission(mission_id='MP-ABC-001', title='My Mission', level=2, risk_level='medium')
    bead = _make_bead()
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['mission_id'] == 'MP-ABC-001'
    assert dispatch['mission_title'] == 'My Mission'
    assert dispatch['mission_level'] == 2
    assert dispatch['mission_risk'] == 'medium'


def test_build_dispatch_populates_bead_fields():
    bead = _make_bead(
        bead_id='BEAD-XYZ-001',
        title='My BEAD',
        agent_role='Reviewer',
        autonomy_level='full',
        risk_level='high',
        reversibility='irreversible',
    )
    dispatch = crg.build_dispatch(_make_mission(), bead)
    assert dispatch['bead_id'] == 'BEAD-XYZ-001'
    assert dispatch['bead_title'] == 'My BEAD'
    assert dispatch['agent_role'] == 'Reviewer'
    assert dispatch['autonomy_level'] == 'full'
    assert dispatch['risk_level'] == 'high'
    assert dispatch['reversibility'] == 'irreversible'


def test_build_dispatch_defaults_for_missing_optional_fields():
    mission = _make_mission()
    # Minimal bead with no optional fields
    bead = {
        'bead_id': 'BEAD-MIN-001',
        'confidence': {'current': 85, 'minimum': 0},
    }
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['allowed_paths'] == []
    assert dispatch['forbidden_paths'] == []
    assert dispatch['tool_budget'] == {}
    assert dispatch['definition_of_done'] == []
    assert dispatch['validation'] == []
    assert dispatch['stop_conditions'] == []
    assert dispatch['required_output'] == []


def test_build_dispatch_confidence_band_blocked_below_40():
    mission = _make_mission()
    bead = _make_bead(confidence={'current': 20, 'minimum': 0})
    dispatch = crg.build_dispatch(mission, bead)
    assert dispatch['confidence_band'] == 'blocked'
    # But dispatch_status is 'ready' because score >= minimum (20 >= 0)
    assert dispatch['dispatch_status'] == 'ready'
