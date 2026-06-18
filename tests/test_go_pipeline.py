"""Tests for scripts/cat_go.py — read-only GO-mode pipeline status driver."""
from __future__ import annotations

import sys
from pathlib import Path

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
