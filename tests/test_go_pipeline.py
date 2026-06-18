"""Tests for scripts/cat_go.py — read-only GO-mode pipeline status driver."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_go


def test_closed_mission_satisfies_all_stages():
    """A fully closed mission (A011) reports all 7 GO-mode stages satisfied."""
    record = cat_go.evaluate('MP-CAT-A011-4C01')
    assert record['mission_status'] == 'closed'
    assert record['bead_count'] == 4
    assert record['stages_satisfied'] == 7
    assert all(s['status'] == 'satisfied' for s in record['stages'].values())


def test_empty_mission_id_is_idle():
    """No active mission -> intent pending, downstream stages n/a, zero satisfied."""
    record = cat_go.evaluate('')
    assert record['mission_id'] is None
    assert record['stages']['intent']['status'] == 'pending'
    assert record['stages']['mission_pack']['status'] == 'na'
    assert record['stages_satisfied'] == 0


def test_unknown_mission_intent_only():
    """An id with no contract: intent satisfied, mission_pack/plan pending."""
    record = cat_go.evaluate('MP-CAT-DOES-NOT-EXIST')
    assert record['stages']['intent']['status'] == 'satisfied'
    assert record['stages']['mission_pack']['status'] == 'pending'
    assert record['stages']['plan_decompose']['status'] == 'pending'
    assert record['stages_satisfied'] == 1


def test_record_shape_is_stable():
    record = cat_go.evaluate('MP-CAT-A011-4C01')
    assert record['kind'] == 'go_run_record'
    assert record['stages_total'] == 7
    assert list(record['stages'].keys()) == cat_go.STAGES


# ---------------------------------------------------------------------------
# Helpers — build a synthetic isolated filesystem for go pipeline tests
# ---------------------------------------------------------------------------

_MISSION_YAML = textwrap.dedent("""\
    mission_id: {mission_id}
    title: GO Pipeline Test Mission
    status: {status}
    level: M2
    owner: Test Owner
    confidence_minimum: 90
    human_gate:
      required: false
""")

_BEAD_YAML = textwrap.dedent("""\
    bead_id: {bead_id}
    mission_id: {mission_id}
    title: GO Pipeline Test BEAD
    status: {status}
    agent_role: Builder
    autonomy_level: L3
    objective: Test objective.
    {validation_block}
""")

_REGISTRY_YAML = textwrap.dedent("""\
    version: 0.1.0
    last_updated: '2026-01-01T00:00:00+00:00'
    active_mission_id: {mission_id}
    missions:
      - mission_id: {mission_id}
        title: GO Pipeline Test Mission
        status: {status}
        level: M2
        priority: 1
        owner: Test Owner
        risk_level: low
        reversibility: high
        autonomy_level: L3
        confidence: 90
        current_bead_id: null
        path: missions/active/{mission_id}.yaml
        created: '2026-01-01'
        last_updated: '2026-01-01'
""")

_TOWER_YAML = textwrap.dedent("""\
    active_mission_id: {mission_id}
    active_bead_id: ''
    status: in_sprint
    last_updated: '2026-01-01T00:00:00+00:00'
""")


def _make_isolated_root(tmp_path, mission_id, mission_status, beads=None):
    """
    Build a minimal isolated filesystem under tmp_path.
    beads: list of (bead_id, bead_status, has_evidence) tuples.
    Returns the tmp_path.
    """
    for d in [
        'missions/active', 'missions/registry',
        'beads/active', 'beads/completed', 'beads/failed',
        'state', 'evidence/go',
    ]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    # Mission contract
    (tmp_path / f'missions/active/{mission_id}.yaml').write_text(
        _MISSION_YAML.format(mission_id=mission_id, status=mission_status),
        encoding='utf-8',
    )

    # Registry
    (tmp_path / 'missions/registry/MISSION_REGISTRY.yaml').write_text(
        _REGISTRY_YAML.format(mission_id=mission_id, status=mission_status),
        encoding='utf-8',
    )

    # Tower state
    (tmp_path / 'state/TOWER_STATE.yaml').write_text(
        _TOWER_YAML.format(mission_id=mission_id),
        encoding='utf-8',
    )

    # BEADs
    for bead_id, bead_status, has_evidence in (beads or []):
        if has_evidence:
            ev_path = tmp_path / 'evidence' / 'bead_evidence.md'
            ev_path.parent.mkdir(parents=True, exist_ok=True)
            ev_path.write_text('evidence content', encoding='utf-8')
            validation_block = textwrap.dedent(f"""\
                validation:
                  - check: output_exists
                    evidence_path: evidence/bead_evidence.md
            """)
        else:
            validation_block = 'validation: []'

        folder = 'beads/active'
        if bead_status in ('completed',):
            folder = 'beads/completed'
        elif bead_status in ('failed', 'archived'):
            folder = 'beads/failed'

        (tmp_path / folder / f'{bead_id}.yaml').write_text(
            _BEAD_YAML.format(
                bead_id=bead_id,
                mission_id=mission_id,
                status=bead_status,
                validation_block=validation_block,
            ),
            encoding='utf-8',
        )

    return tmp_path


# ---------------------------------------------------------------------------
# Stage 1: Intent
# ---------------------------------------------------------------------------

class TestStageIntent:

    def test_intent_satisfied_when_mission_id_provided(self, tmp_path):
        mid = 'MP-GO-001'
        _make_isolated_root(tmp_path, mid, 'in_progress')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['intent']['status'] == 'satisfied'
        assert mid in record['stages']['intent']['detail']

    def test_intent_pending_when_no_mission_id(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml'):
            record = cat_go.evaluate('')
        assert record['stages']['intent']['status'] == 'pending'
        assert 'no active mission' in record['stages']['intent']['detail']


# ---------------------------------------------------------------------------
# Stage 2: Mission Pack
# ---------------------------------------------------------------------------

class TestStageMissionPack:

    def test_mission_pack_satisfied_when_contract_found(self, tmp_path):
        mid = 'MP-GO-002'
        _make_isolated_root(tmp_path, mid, 'approved')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['mission_pack']['status'] == 'satisfied'

    def test_mission_pack_pending_when_no_contract(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate('MP-DOES-NOT-EXIST-GO')
        assert record['stages']['mission_pack']['status'] == 'pending'
        assert 'not found' in record['stages']['mission_pack']['detail']

    def test_mission_pack_na_when_no_mission_id(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml'):
            record = cat_go.evaluate('')
        assert record['stages']['mission_pack']['status'] == 'na'


# ---------------------------------------------------------------------------
# Stage 3: Plan & Decompose
# ---------------------------------------------------------------------------

class TestStagePlanDecompose:

    def test_plan_decompose_satisfied_when_beads_exist(self, tmp_path):
        mid = 'MP-GO-003'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-003-001', 'active', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['plan_decompose']['status'] == 'satisfied'
        assert '1 BEAD' in record['stages']['plan_decompose']['detail']

    def test_plan_decompose_pending_when_no_beads(self, tmp_path):
        mid = 'MP-GO-003B'
        _make_isolated_root(tmp_path, mid, 'approved')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['plan_decompose']['status'] == 'pending'

    def test_plan_decompose_na_when_no_mission(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml'):
            record = cat_go.evaluate('')
        assert record['stages']['plan_decompose']['status'] == 'na'


# ---------------------------------------------------------------------------
# Stage 4: Execute
# ---------------------------------------------------------------------------

class TestStageExecute:

    def test_execute_satisfied_when_bead_started(self, tmp_path):
        mid = 'MP-GO-004'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-004-001', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['execute']['status'] == 'satisfied'

    def test_execute_pending_when_bead_queued(self, tmp_path):
        mid = 'MP-GO-004B'
        _make_isolated_root(tmp_path, mid, 'approved', beads=[
            ('BEAD-GO-004B-001', 'queued', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['execute']['status'] == 'pending'
        assert 'none started' in record['stages']['execute']['detail']

    def test_execute_na_when_no_beads(self, tmp_path):
        mid = 'MP-GO-004C'
        _make_isolated_root(tmp_path, mid, 'approved')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['execute']['status'] == 'na'

    def test_execute_satisfied_when_bead_validating(self, tmp_path):
        mid = 'MP-GO-004D'
        _make_isolated_root(tmp_path, mid, 'validating', beads=[
            ('BEAD-GO-004D-001', 'validating', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['execute']['status'] == 'satisfied'

    def test_execute_partial_started_still_satisfied(self, tmp_path):
        """If at least one BEAD started, execute is satisfied even if others are queued."""
        mid = 'MP-GO-004E'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-004E-001', 'queued', False),
            ('BEAD-GO-004E-002', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['execute']['status'] == 'satisfied'


# ---------------------------------------------------------------------------
# Stage 5: Observe & Capture
# ---------------------------------------------------------------------------

class TestStageObserveCapture:

    def test_observe_capture_satisfied_when_bead_has_evidence(self, tmp_path):
        mid = 'MP-GO-005'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-005-001', 'in_progress', True),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['observe_capture']['status'] == 'satisfied'

    def test_observe_capture_pending_when_no_evidence(self, tmp_path):
        mid = 'MP-GO-005B'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-005B-001', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['observe_capture']['status'] == 'pending'

    def test_observe_capture_na_when_no_beads(self, tmp_path):
        mid = 'MP-GO-005C'
        _make_isolated_root(tmp_path, mid, 'approved')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['observe_capture']['status'] == 'na'

    def test_observe_capture_counts_partial_evidence(self, tmp_path):
        """If only some BEADs have evidence, observe_capture is still satisfied."""
        mid = 'MP-GO-005D'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-005D-001', 'in_progress', True),
            ('BEAD-GO-005D-002', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['observe_capture']['status'] == 'satisfied'
        assert '1/2' in record['stages']['observe_capture']['detail']


# ---------------------------------------------------------------------------
# Stage 6: Score & Validate
# ---------------------------------------------------------------------------

class TestStageScoreValidate:

    def test_score_validate_satisfied_when_all_beads_validated(self, tmp_path):
        mid = 'MP-GO-006'
        _make_isolated_root(tmp_path, mid, 'validating', beads=[
            ('BEAD-GO-006-001', 'completed', True),
            ('BEAD-GO-006-002', 'reviewed', True),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['score_validate']['status'] == 'satisfied'

    def test_score_validate_pending_when_bead_in_progress(self, tmp_path):
        mid = 'MP-GO-006B'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-006B-001', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['score_validate']['status'] == 'pending'

    def test_score_validate_na_when_no_beads(self, tmp_path):
        mid = 'MP-GO-006C'
        _make_isolated_root(tmp_path, mid, 'approved')
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['score_validate']['status'] == 'na'

    def test_score_validate_pending_detail_counts_unvalidated(self, tmp_path):
        mid = 'MP-GO-006D'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-006D-001', 'validating', False),
            ('BEAD-GO-006D-002', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path):
            record = cat_go.evaluate(mid)
        assert record['stages']['score_validate']['status'] == 'pending'
        assert '1 BEAD' in record['stages']['score_validate']['detail'] or \
               '2 BEAD' in record['stages']['score_validate']['detail']


# ---------------------------------------------------------------------------
# Stage 7: Continue / Close
# ---------------------------------------------------------------------------

class TestStageContinueClose:

    def test_continue_close_satisfied_when_mission_closed(self, tmp_path):
        mid = 'MP-GO-007'
        _make_isolated_root(tmp_path, mid, 'closed', beads=[
            ('BEAD-GO-007-001', 'completed', True),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['stages']['continue_close']['status'] == 'satisfied'

    def test_continue_close_satisfied_when_all_beads_terminal(self, tmp_path):
        mid = 'MP-GO-007B'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-007B-001', 'archived', True),
            ('BEAD-GO-007B-002', 'completed', True),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['stages']['continue_close']['status'] == 'satisfied'
        assert 'terminal' in record['stages']['continue_close']['detail']

    def test_continue_close_pending_when_mission_open(self, tmp_path):
        mid = 'MP-GO-007C'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-007C-001', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['stages']['continue_close']['status'] == 'pending'

    def test_continue_close_na_when_no_mission(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml'), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate('')
        assert record['stages']['continue_close']['status'] == 'na'

    def test_continue_close_mission_abandoned_is_satisfied(self, tmp_path):
        mid = 'MP-GO-007D'
        _make_isolated_root(tmp_path, mid, 'abandoned')
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['stages']['continue_close']['status'] == 'satisfied'


# ---------------------------------------------------------------------------
# GO / NO-GO decision logic — stages_satisfied count
# ---------------------------------------------------------------------------

class TestGoDecision:

    def test_all_stages_satisfied_when_fully_done(self, tmp_path):
        mid = 'MP-GO-FINAL'
        _make_isolated_root(tmp_path, mid, 'closed', beads=[
            ('BEAD-GO-FINAL-001', 'archived', True),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['stages_satisfied'] == 7

    def test_zero_stages_satisfied_when_idle(self, tmp_path):
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.TOWER_STATE_PATH', tmp_path / 'state/TOWER_STATE.yaml'), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate('')
        assert record['stages_satisfied'] == 0

    def test_stages_satisfied_count_matches_stage_statuses(self, tmp_path):
        mid = 'MP-GO-COUNT'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-COUNT-001', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        computed = sum(1 for s in record['stages'].values() if s['status'] == 'satisfied')
        assert record['stages_satisfied'] == computed

    def test_partial_pipeline_partial_satisfied(self, tmp_path):
        """With contract + BEADs queued: intent + mission_pack + plan_decompose = 3."""
        mid = 'MP-GO-PART'
        _make_isolated_root(tmp_path, mid, 'approved', beads=[
            ('BEAD-GO-PART-001', 'queued', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        # intent, mission_pack, plan_decompose are satisfied; execute/observe/validate/close pending
        assert record['stages']['intent']['status'] == 'satisfied'
        assert record['stages']['mission_pack']['status'] == 'satisfied'
        assert record['stages']['plan_decompose']['status'] == 'satisfied'
        assert record['stages']['execute']['status'] == 'pending'
        assert record['stages_satisfied'] == 3


# ---------------------------------------------------------------------------
# Record schema & metadata
# ---------------------------------------------------------------------------

class TestRecordSchema:

    def test_record_has_all_required_keys(self, tmp_path):
        mid = 'MP-GO-SCHEMA'
        _make_isolated_root(tmp_path, mid, 'in_progress')
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        for key in ('kind', 'timestamp', 'mission_id', 'mission_status',
                    'bead_count', 'stages', 'stages_satisfied', 'stages_total'):
            assert key in record, f'Missing key {key!r}'

    def test_stages_keys_match_stages_constant(self, tmp_path):
        mid = 'MP-GO-KEYS'
        _make_isolated_root(tmp_path, mid, 'in_progress')
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert list(record['stages'].keys()) == cat_go.STAGES

    def test_each_stage_has_status_and_detail(self, tmp_path):
        mid = 'MP-GO-DETAIL'
        _make_isolated_root(tmp_path, mid, 'in_progress')
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        for name, stage in record['stages'].items():
            assert 'status' in stage, f'Stage {name!r} missing status'
            assert 'detail' in stage, f'Stage {name!r} missing detail'
            assert stage['status'] in ('satisfied', 'pending', 'na'), \
                f"Stage {name!r} has unexpected status {stage['status']!r}"

    def test_bead_count_matches_actual_beads(self, tmp_path):
        mid = 'MP-GO-BCOUNT'
        _make_isolated_root(tmp_path, mid, 'in_progress', beads=[
            ('BEAD-GO-BC-001', 'active', False),
            ('BEAD-GO-BC-002', 'active', False),
            ('BEAD-GO-BC-003', 'in_progress', False),
        ])
        with mock.patch('cat_go.ROOT', tmp_path), \
             mock.patch('cat_go.REGISTRY_PATH', tmp_path / 'missions/registry/MISSION_REGISTRY.yaml'):
            record = cat_go.evaluate(mid)
        assert record['bead_count'] == 3
