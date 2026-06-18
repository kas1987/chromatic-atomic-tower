"""Tests for scripts/cat_resolve_go.py selection and dispatch logic.

Covers the pure decision functions — mission selection ordering, BEAD selection,
confidence banding, dispatch-packet construction, and the markdown renderer.
The ``main`` entry point performs filesystem and subprocess I/O and is not
exercised here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_resolve_go as rg  # noqa: E402


# ---------------------------------------------------------------------------
# select_mission
# ---------------------------------------------------------------------------

def test_select_mission_none_when_no_approved():
    registry = {"missions": [{"mission_id": "M1", "status": "draft"}]}
    assert rg.select_mission(registry) is None


def test_select_mission_prefers_lowest_priority_number():
    registry = {"missions": [
        {"mission_id": "LOW", "status": "approved", "priority": 5},
        {"mission_id": "HIGH", "status": "approved", "priority": 1},
    ]}
    assert rg.select_mission(registry)["mission_id"] == "HIGH"


def test_select_mission_tiebreak_by_confidence_then_risk():
    registry = {"missions": [
        {"mission_id": "A", "status": "approved", "priority": 1,
         "confidence": 50, "risk_level": "high"},
        {"mission_id": "B", "status": "approved", "priority": 1,
         "confidence": 90, "risk_level": "high"},
    ]}
    # higher confidence wins at equal priority
    assert rg.select_mission(registry)["mission_id"] == "B"


def test_select_mission_accepts_all_allowed_statuses():
    for status in rg.ALLOWED_MISSION_STATUSES:
        registry = {"missions": [{"mission_id": "X", "status": status, "priority": 1}]}
        assert rg.select_mission(registry)["mission_id"] == "X"


# ---------------------------------------------------------------------------
# select_bead
# ---------------------------------------------------------------------------

def test_select_bead_prefers_current_bead_id():
    mission = {"mission_id": "M1", "current_bead_id": "B-2"}
    beads = [
        {"bead_id": "B-1", "mission_id": "M1", "status": "active"},
        {"bead_id": "B-2", "mission_id": "M1", "status": "active"},
    ]
    assert rg.select_bead(mission, beads, allow_queued=False)["bead_id"] == "B-2"


def test_select_bead_falls_back_to_first_active():
    mission = {"mission_id": "M1"}
    beads = [
        {"bead_id": "B-1", "mission_id": "M1", "status": "active"},
        {"bead_id": "B-2", "mission_id": "OTHER", "status": "active"},
    ]
    assert rg.select_bead(mission, beads, allow_queued=False)["bead_id"] == "B-1"


def test_select_bead_none_when_no_active():
    mission = {"mission_id": "M1"}
    beads = [{"bead_id": "B-1", "mission_id": "M1", "status": "queued"}]
    assert rg.select_bead(mission, beads, allow_queued=False) is None


def test_select_bead_allow_queued_still_requires_active_for_return():
    # allow_queued widens the candidate filter, but the function only returns
    # a bead whose status is 'active' (queued candidates are not auto-returned
    # unless they match current_bead_id).
    mission = {"mission_id": "M1", "current_bead_id": "B-Q"}
    beads = [{"bead_id": "B-Q", "mission_id": "M1", "status": "queued"}]
    assert rg.select_bead(mission, beads, allow_queued=True)["bead_id"] == "B-Q"


# ---------------------------------------------------------------------------
# confidence_band
# ---------------------------------------------------------------------------

import pytest  # noqa: E402


@pytest.mark.parametrize("score,band", [
    (95, "very_high"),
    (90, "very_high"),
    (80, "high"),
    (65, "medium"),
    (45, "low"),
    (10, "blocked"),
])
def test_confidence_band(score, band):
    assert rg.confidence_band(score) == band


# ---------------------------------------------------------------------------
# build_dispatch
# ---------------------------------------------------------------------------

def _bead(current=80, minimum=60):
    return {
        "bead_id": "BEAD-CAT-S001-4C01-01",
        "title": "Do work",
        "status": "active",
        "agent_role": "BUILDER",
        "autonomy_level": "L2",
        "confidence": {"current": current, "minimum": minimum},
        "risk_level": "low",
        "reversibility": "high",
        "allowed_paths": ["scripts/"],
        "forbidden_paths": [".env"],
        "tool_budget": {"max_calls": 10},
        "definition_of_done": ["done"],
        "validation": [{"type": "test", "command": "pytest", "evidence_path": "e.txt"}],
        "stop_conditions": ["timeout"],
        "required_output": ["report"],
        "_path": "beads/active/BEAD-CAT-S001-4C01-01.yaml",
    }


def _mission():
    return {
        "mission_id": "MP-CAT-S001-4C01",
        "title": "Mission",
        "level": "M2",
        "risk_level": "low",
        "path": "missions/backlog/m.yaml",
    }


def test_build_dispatch_ready_when_confidence_meets_minimum():
    d = rg.build_dispatch(_mission(), _bead(current=80, minimum=60))
    assert d["dispatch_status"] == "ready"
    assert d["confidence_band"] == "high"
    assert d["bead_id"] == "BEAD-CAT-S001-4C01-01"
    assert d["allowed_paths"] == ["scripts/"]


def test_build_dispatch_blocked_when_below_minimum():
    d = rg.build_dispatch(_mission(), _bead(current=40, minimum=60))
    assert d["dispatch_status"] == "blocked"
    assert "below minimum" in d["reason"]


def test_build_dispatch_handles_missing_confidence():
    bead = _bead()
    del bead["confidence"]
    d = rg.build_dispatch(_mission(), bead)
    assert d["confidence"] == 0
    assert d["dispatch_status"] == "ready"  # 0 >= 0


# ---------------------------------------------------------------------------
# print_markdown
# ---------------------------------------------------------------------------

def test_print_markdown_renders_sections(capsys):
    d = rg.build_dispatch(_mission(), _bead())
    rg.print_markdown(d)
    out = capsys.readouterr().out
    assert "# CAT GO Dispatch Packet" in out
    assert "## Allowed Paths" in out
    assert "## Definition of Done" in out
    assert "BEAD-CAT-S001-4C01-01" in out
    assert "pytest" in out
