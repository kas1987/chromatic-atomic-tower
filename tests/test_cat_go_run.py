"""Coverage for cat_go_run.py pure helper functions.

next_actionable_stage and plan_action are pure functions that cover
most of the business logic without needing subprocess or filesystem.
"""
from __future__ import annotations

import pytest

from scripts.cat_go_run import next_actionable_stage, plan_action


# ---------------------------------------------------------------------------
# Minimal stage record helpers
# ---------------------------------------------------------------------------

def _record(stage_statuses: dict[str, str], bead_count: int = 0, close_detail: str = '') -> dict:
    from cat_go import STAGES
    stages = {}
    for s in STAGES:
        status = stage_statuses.get(s, 'pending')
        entry: dict = {'status': status}
        if s == 'continue_close' and close_detail:
            entry['detail'] = close_detail
        stages[s] = entry
    return {'stages': stages, 'bead_count': bead_count}


class TestNextActionableStage:
    def test_returns_none_when_all_satisfied(self):
        from cat_go import STAGES
        rec = _record({s: 'satisfied' for s in STAGES})
        assert next_actionable_stage(rec) is None

    def test_returns_first_pending_stage(self):
        from cat_go import STAGES
        # Make first stage pending, rest satisfied
        statuses = {s: 'satisfied' for s in STAGES}
        statuses[STAGES[0]] = 'pending'
        rec = _record(statuses)
        assert next_actionable_stage(rec) == STAGES[0]

    def test_returns_none_on_empty_stages(self):
        assert next_actionable_stage({'stages': {}}) is None

    def test_picks_earliest_pending(self):
        from cat_go import STAGES
        if len(STAGES) < 2:
            pytest.skip("Need at least 2 stages")
        statuses = {s: 'satisfied' for s in STAGES}
        statuses[STAGES[-1]] = 'pending'
        rec = _record(statuses)
        assert next_actionable_stage(rec) == STAGES[-1]


class TestPlanAction:
    def test_all_satisfied_returns_none_kind(self):
        from cat_go import STAGES
        rec = _record({s: 'satisfied' for s in STAGES})
        plan = plan_action(rec)
        assert plan['kind'] == 'none'
        assert plan['automatable'] is False
        assert plan['next_stage'] is None

    def test_score_validate_returns_check_kind(self):
        from cat_go import STAGES
        statuses = {s: 'satisfied' for s in STAGES}
        statuses['score_validate'] = 'pending'
        rec = _record(statuses)
        plan = plan_action(rec)
        assert plan['next_stage'] == 'score_validate'
        assert plan['kind'] == 'check'
        assert plan['automatable'] is True
        assert 'cat_validate' in plan['action']

    def test_continue_close_automatable_when_ready(self):
        from cat_go import STAGES
        statuses = {s: 'satisfied' for s in STAGES}
        statuses['continue_close'] = 'pending'
        rec = _record(statuses, bead_count=2)
        plan = plan_action(rec)
        assert plan['next_stage'] == 'continue_close'
        assert plan['kind'] == 'mutate'
        assert plan['automatable'] is True
        assert 'cat_sprint_closeout' in plan['action']

    def test_continue_close_not_automatable_when_bead_count_zero(self):
        from cat_go import STAGES
        statuses = {s: 'satisfied' for s in STAGES}
        statuses['continue_close'] = 'pending'
        rec = _record(statuses, bead_count=0)
        plan = plan_action(rec)
        # bead_count == 0 → falls through to manual
        assert plan['kind'] == 'manual'
        assert plan['automatable'] is False

    def test_continue_close_automatable_via_ready_hint(self):
        from cat_go import STAGES
        # Some stages are 'failed' (not pending, so next_actionable returns continue_close),
        # but 'failed' ≠ 'satisfied'/'na' → other_stages_ok=False.
        # The 'ready to close' detail hint makes continue_close automatable anyway.
        statuses = {s: 'failed' for s in STAGES}
        statuses['continue_close'] = 'pending'
        rec = _record(statuses, bead_count=1, close_detail='ready to close')
        plan = plan_action(rec)
        assert plan['next_stage'] == 'continue_close'
        assert plan['automatable'] is True

    def test_manual_stage_returns_manual_kind(self):
        from cat_go import STAGES
        # Find a stage that's not score_validate or continue_close
        manual_stage = next(
            (s for s in STAGES if s not in ('score_validate', 'continue_close')),
            None,
        )
        if manual_stage is None:
            pytest.skip("No manual stages to test")
        statuses = {s: 'satisfied' for s in STAGES}
        statuses[manual_stage] = 'pending'
        rec = _record(statuses)
        plan = plan_action(rec)
        assert plan['kind'] == 'manual'
        assert plan['automatable'] is False
        assert manual_stage in plan['action']

    def test_plan_always_has_required_keys(self):
        from cat_go import STAGES
        rec = _record({s: 'pending' for s in STAGES})
        plan = plan_action(rec)
        for key in ('next_stage', 'action', 'automatable', 'kind', 'reason'):
            assert key in plan
