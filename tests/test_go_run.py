"""Tests for scripts/cat_go_run.py — active GO-mode orchestrator (G-1a).

All tests are read-only / dry-run; no state is mutated.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_go_run


# ---------------------------------------------------------------------------
# Helpers for building synthetic records
# ---------------------------------------------------------------------------

def _make_record(
    stage_statuses: dict[str, str] | None = None,
    *,
    mission_status: str = 'active',
    bead_count: int = 3,
) -> dict:
    """Build a minimal synthetic record matching evaluate()'s output shape."""
    default_status = 'satisfied'
    stages = {
        name: {
            'status': (stage_statuses or {}).get(name, default_status),
            'detail': f'synthetic detail for {name}',
        }
        for name in cat_go_run.STAGES
    }
    satisfied = sum(1 for s in stages.values() if s['status'] == 'satisfied')
    return {
        'kind': 'go_run_record',
        'timestamp': '2026-01-01T00:00:00+00:00',
        'mission_id': 'MP-CAT-TEST-4C01',
        'mission_status': mission_status,
        'bead_count': bead_count,
        'stages': stages,
        'stages_satisfied': satisfied,
        'stages_total': len(cat_go_run.STAGES),
    }


# ---------------------------------------------------------------------------
# next_actionable_stage
# ---------------------------------------------------------------------------

def test_next_actionable_stage_returns_none_when_all_satisfied():
    """next_actionable_stage returns None when every stage is 'satisfied'."""
    record = _make_record()  # all satisfied by default
    result = cat_go_run.next_actionable_stage(record)
    assert result is None


def test_next_actionable_stage_returns_first_pending():
    """next_actionable_stage returns the FIRST pending stage in STAGES order."""
    # Make execute and score_validate pending; everything else satisfied.
    statuses = {name: 'satisfied' for name in cat_go_run.STAGES}
    statuses['execute'] = 'pending'
    statuses['score_validate'] = 'pending'
    record = _make_record(statuses)
    result = cat_go_run.next_actionable_stage(record)
    # 'execute' comes before 'score_validate' in STAGES
    assert result == 'execute'


# ---------------------------------------------------------------------------
# plan_action
# ---------------------------------------------------------------------------

def test_plan_action_none_for_closed_mission():
    """plan_action on the real closed mission (A011, 7/7 satisfied) returns action='none'."""
    rec = cat_go_run.evaluate('MP-CAT-A011-4C01')
    result = cat_go_run.plan_action(rec)
    assert result['action'] == 'none'
    assert result['automatable'] is False
    assert result['next_stage'] is None


def test_plan_action_automatable_close_when_only_continue_close_pending():
    """plan_action picks an automatable close action when only continue_close is pending."""
    # All stages satisfied except continue_close which is pending.
    statuses = {name: 'satisfied' for name in cat_go_run.STAGES}
    statuses['continue_close'] = 'pending'
    # Use a detail that hints at ready-to-close (alternative condition)
    record = _make_record(statuses, bead_count=4, mission_status='active')
    # Override the continue_close detail to include 'ready to close' hint.
    record['stages']['continue_close']['detail'] = 'all BEADs terminal — ready to close'

    result = cat_go_run.plan_action(record)
    assert result['automatable'] is True
    assert result['action'] == 'run cat_sprint_closeout.py'
    assert result['next_stage'] == 'continue_close'


def test_plan_action_automatable_close_other_stages_satisfied():
    """plan_action is automatable when bead_count>0 and all other stages satisfied/na."""
    statuses = {name: 'satisfied' for name in cat_go_run.STAGES}
    statuses['continue_close'] = 'pending'
    # Make one stage 'na' to confirm na is also acceptable.
    statuses['plan_decompose'] = 'na'
    record = _make_record(statuses, bead_count=2, mission_status='active')

    result = cat_go_run.plan_action(record)
    assert result['automatable'] is True
    assert result['action'] == 'run cat_sprint_closeout.py'


def test_plan_action_manual_for_non_close_pending():
    """plan_action returns manual action for a non-close pending stage."""
    statuses = {name: 'satisfied' for name in cat_go_run.STAGES}
    statuses['score_validate'] = 'pending'
    statuses['continue_close'] = 'pending'
    record = _make_record(statuses, bead_count=3, mission_status='active')

    result = cat_go_run.plan_action(record)
    # score_validate comes before continue_close in STAGES, so it's the next.
    assert result['automatable'] is False
    assert result['next_stage'] == 'score_validate'
    assert 'manual' in result['action']
