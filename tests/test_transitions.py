#!/usr/bin/env python3
"""
test_transitions.py — test suite for cat_transition.py.

All tests run against an isolated fixture directory (tmp_path).
CAT_ROOT env var is set so common.ROOT and all derived paths resolve
through the fixture rather than the live repo.

CLI (new): --type {mission,bead} --id ID --to STATE --reason TEXT
           [--evidence TEXT] [--actor TEXT] [--dry-run] [--move] [--json]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = ROOT / "scripts"
TRANSITION_SCRIPT = SCRIPTS_DIR / "cat_transition.py"
REAL_RULES_PATH = ROOT / "gates" / "state" / "STATE_TRANSITION_RULES.yaml"


# ---------------------------------------------------------------------------
# Fixture YAML content
# ---------------------------------------------------------------------------

_REGISTRY_YAML = textwrap.dedent("""\
    version: 0.1.0
    last_updated: '2026-01-01T00:00:00+00:00'
    active_mission_id: MP-TEST-001
    selection_policy:
      priority_order: [approved, in_progress, validating]
      tie_breakers: [highest_priority]
    missions:
      - mission_id: MP-TEST-001
        title: Test Mission Approved
        level: M3
        status: approved
        priority: 1
        owner: Test Owner
        risk_level: low
        reversibility: high
        autonomy_level: L3
        confidence: 90
        current_bead_id: BEAD-TEST-001
        path: missions/active/MP-TEST-001.yaml
        created: '2026-01-01'
        last_updated: '2026-01-01'
      - mission_id: MP-TEST-DRAFT
        title: Test Mission Draft
        level: M3
        status: draft
        priority: 2
        owner: Test Owner
        risk_level: low
        reversibility: high
        autonomy_level: L3
        confidence: 90
        current_bead_id: null
        path: missions/active/MP-TEST-DRAFT.yaml
        created: '2026-01-01'
        last_updated: '2026-01-01'
      - mission_id: MP-TEST-TRIAGED
        title: Test Mission Triaged
        level: M3
        status: triaged
        priority: 3
        owner: Test Owner
        risk_level: low
        reversibility: high
        autonomy_level: L3
        confidence: 90
        current_bead_id: null
        path: missions/active/MP-TEST-TRIAGED.yaml
        created: '2026-01-01'
        last_updated: '2026-01-01'
      - mission_id: MP-TEST-BLOCKED
        title: Test Mission Blocked
        level: M3
        status: blocked
        priority: 4
        owner: Test Owner
        risk_level: low
        reversibility: high
        autonomy_level: L3
        confidence: 90
        current_bead_id: null
        path: missions/active/MP-TEST-BLOCKED.yaml
        created: '2026-01-01'
        last_updated: '2026-01-01'
""")

_MISSION_YAML_TMPL = textwrap.dedent("""\
    mission_id: {mission_id}
    title: {title}
    status: {status}
    level: M3
    owner: Test Owner
    confidence_minimum: 90
    human_gate:
      required: false
""")

_BEAD_YAML_TMPL = textwrap.dedent("""\
    bead_id: {bead_id}
    mission_id: MP-TEST-001
    title: Test BEAD
    status: {status}
    agent_role: Worker
    autonomy_level: L3
    objective: Test objective.
    allowed_paths:
      - docs/**
    forbidden_paths:
      - .env
""")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cat_root(tmp_path):
    """Isolated CAT root with controlled fixture states, fresh per test."""
    if not REAL_RULES_PATH.exists():
        pytest.skip("STATE_TRANSITION_RULES.yaml not found")

    for d in [
        "gates/state", "missions/registry", "missions/active",
        "beads/active", "evidence/logs", "evidence/transitions",
        "evidence/snapshots", "evidence/rollbacks",
    ]:
        (tmp_path / d).mkdir(parents=True)

    shutil.copy2(REAL_RULES_PATH, tmp_path / "gates" / "state" / "STATE_TRANSITION_RULES.yaml")

    (tmp_path / "missions" / "registry" / "MISSION_REGISTRY.yaml").write_text(
        _REGISTRY_YAML, encoding="utf-8"
    )

    for mid, title, status in [
        ("MP-TEST-001",     "Approved Mission", "approved"),
        ("MP-TEST-DRAFT",   "Draft Mission",    "draft"),
        ("MP-TEST-TRIAGED", "Triaged Mission",  "triaged"),
        ("MP-TEST-BLOCKED", "Blocked Mission",  "blocked"),
    ]:
        (tmp_path / "missions" / "active" / f"{mid}.yaml").write_text(
            _MISSION_YAML_TMPL.format(mission_id=mid, title=title, status=status),
            encoding="utf-8",
        )

    for bead_id, status in [
        ("BEAD-TEST-001", "queued"),
        ("BEAD-TEST-CR",  "changes_requested"),
        ("BEAD-TEST-FAIL","failed"),
        ("BEAD-TEST-IP",  "in_progress"),
    ]:
        (tmp_path / "beads" / "active" / f"{bead_id}.yaml").write_text(
            _BEAD_YAML_TMPL.format(bead_id=bead_id, status=status),
            encoding="utf-8",
        )

    return tmp_path


def run_transition(args: list[str], cat_root: Path) -> tuple[int, str, str]:
    env = {**os.environ, "CAT_ROOT": str(cat_root)}
    result = subprocess.run(
        ["python", str(TRANSITION_SCRIPT)] + args,
        cwd=str(ROOT), capture_output=True, text=True, env=env,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Mission transition tests
# ---------------------------------------------------------------------------


class TestMissionTransitions:

    def test_valid_mission_draft_to_triaged(self, cat_root):
        exit_code, stdout, stderr = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-DRAFT",
            "--to", "triaged", "--reason", "test",
        ], cat_root)
        assert exit_code == 0, f"Expected exit 0. stderr: {stderr}"
        assert "draft" in stdout and "triaged" in stdout

    def test_invalid_mission_transition_nonexistent_arc(self, cat_root):
        # draft → learned is not a valid arc
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-DRAFT",
            "--to", "learned", "--reason", "test",
        ], cat_root)
        assert exit_code == 1

    def test_invalid_mission_transition_from_wrong_state(self, cat_root):
        # MP-TEST-001 is 'approved'; approved → triaged is not in rules
        exit_code, stdout, stderr = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "triaged", "--reason", "test",
        ], cat_root)
        assert exit_code == 1
        assert "not allowed" in stdout.lower() or "not allowed" in stderr.lower()

    def test_mission_dry_run_no_mutation(self, cat_root):
        registry_path = cat_root / "missions" / "registry" / "MISSION_REGISTRY.yaml"
        contract_path = cat_root / "missions" / "active" / "MP-TEST-001.yaml"
        before_reg = registry_path.read_text(encoding="utf-8")
        before_con = contract_path.read_text(encoding="utf-8")
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "test",
        ], cat_root)
        assert exit_code == 0
        assert registry_path.read_text(encoding="utf-8") == before_reg, "dry-run must not mutate registry"
        assert contract_path.read_text(encoding="utf-8") == before_con, "dry-run must not mutate contract"

    def test_mission_blocking_from_approved(self, cat_root):
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "test",
        ], cat_root)
        assert exit_code == 0, f"Expected valid blocking arc. stderr: {stderr}"

    def test_mission_unblocking(self, cat_root):
        # blocked → approved is a valid arc in STATE_TRANSITION_RULES
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-BLOCKED",
            "--to", "approved", "--reason", "unblock test",
        ], cat_root)
        assert exit_code == 0, f"Expected valid unblocking arc. stderr: {stderr}"


# ---------------------------------------------------------------------------
# BEAD transition tests
# ---------------------------------------------------------------------------


class TestBEADTransitions:

    def test_valid_bead_queued_to_active(self, cat_root):
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-001",
            "--to", "active", "--reason", "test",
        ], cat_root)
        assert exit_code == 0, f"Expected valid transition. stderr: {stderr}"

    def test_invalid_bead_transition_nonexistent_arc(self, cat_root):
        # queued → failed is not a valid arc (queued allows: active, blocked, archived)
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-001",
            "--to", "failed", "--reason", "test",
        ], cat_root)
        assert exit_code == 1

    def test_bead_progress_happy_path(self, cat_root):
        # execute mode: each step sees the state written by the previous one
        exit_code1, _, err1 = run_transition([
            "--execute", "--type", "bead", "--id", "BEAD-TEST-001",
            "--to", "active", "--reason", "step 1",
        ], cat_root)
        assert exit_code1 == 0, f"queued→active failed: {err1}"

        exit_code2, _, err2 = run_transition([
            "--execute", "--type", "bead", "--id", "BEAD-TEST-001",
            "--to", "in_progress", "--reason", "step 2",
        ], cat_root)
        assert exit_code2 == 0, f"active→in_progress failed: {err2}"

    def test_bead_rework_loop(self, cat_root):
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-CR",
            "--to", "in_progress", "--reason", "rework test",
        ], cat_root)
        assert exit_code == 0, f"Expected valid rework arc. stderr: {stderr}"

    def test_bead_terminal_from_failed(self, cat_root):
        # failed → archived: only valid onward arc from failed
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-FAIL",
            "--to", "archived", "--reason", "cleanup",
        ], cat_root)
        assert exit_code == 0, f"Expected valid failed→archived arc. stderr: {stderr}"


# ---------------------------------------------------------------------------
# Evidence gate tests (replaces guard tests)
# ---------------------------------------------------------------------------


class TestEvidenceGate:

    def test_no_evidence_required_for_basic_transitions(self, cat_root):
        # queued → active does not require evidence
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-001",
            "--to", "active", "--reason", "evidence gate test",
        ], cat_root)
        assert exit_code == 0, f"Basic transition should not require evidence. stderr: {stderr}"

    def test_evidence_required_blocks_transition(self, cat_root):
        # in_progress → validating requires evidence; omitting it must be rejected
        exit_code, stdout, _ = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-IP",
            "--to", "validating", "--reason", "evidence gate test",
        ], cat_root)
        assert exit_code == 1
        assert "evidence" in stdout.lower()

    def test_evidence_provided_allows_transition(self, cat_root):
        # in_progress → validating with --evidence passes the gate
        exit_code, _, stderr = run_transition([
            "--dry-run", "--type", "bead", "--id", "BEAD-TEST-IP",
            "--to", "validating", "--reason", "evidence gate test",
            "--evidence", "evidence/reports/test.md",
        ], cat_root)
        assert exit_code == 0, f"Transition with evidence should be allowed. stderr: {stderr}"


# ---------------------------------------------------------------------------
# Dry-run vs execute mode tests
# ---------------------------------------------------------------------------


class TestDryRunVsExecute:

    def test_mode_flag_required(self, cat_root):
        # neither --dry-run nor --execute → exit 2 (argparse)
        exit_code, _, _ = run_transition([
            "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "test",
        ], cat_root)
        assert exit_code != 0

    def test_execute_mutates_contract(self, cat_root):
        contract = cat_root / "missions" / "active" / "MP-TEST-001.yaml"
        assert "approved" in contract.read_text(encoding="utf-8")
        exit_code, _, stderr = run_transition([
            "--execute", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "execute test",
        ], cat_root)
        assert exit_code == 0, f"stderr: {stderr}"
        assert "blocked" in contract.read_text(encoding="utf-8")

    def test_dry_run_does_not_mutate_contract(self, cat_root):
        contract = cat_root / "missions" / "active" / "MP-TEST-001.yaml"
        before = contract.read_text(encoding="utf-8")
        run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "dry-run test",
        ], cat_root)
        assert contract.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_entity_not_found(self, cat_root):
        exit_code, stdout, stderr = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-NONEXISTENT",
            "--to", "triaged", "--reason", "test",
        ], cat_root)
        assert exit_code != 0
        combined = (stdout + stderr).lower()
        assert "not found" in combined or "error" in combined

    def test_missing_required_to_arg(self, cat_root):
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--reason", "test",
        ], cat_root)
        assert exit_code != 0

    def test_invalid_to_state(self, cat_root):
        # 'invalid_state' is not in the statuses list → exit 1
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "invalid_state", "--reason", "test",
        ], cat_root)
        assert exit_code != 0

    def test_invalid_type(self, cat_root):
        exit_code, _, _ = run_transition([
            "--dry-run", "--type", "invalid_type", "--id", "MP-TEST-001",
            "--to", "triaged", "--reason", "test",
        ], cat_root)
        assert exit_code != 0


# ---------------------------------------------------------------------------
# Evidence logging tests
# ---------------------------------------------------------------------------


class TestEvidenceLogging:

    def test_rejected_transition_logs_evidence(self, cat_root):
        # Rejected transitions (allowed=False) always log to the audit trail
        run_transition([
            "--dry-run", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "triaged", "--reason", "rejected test",
        ], cat_root)
        log = cat_root / "evidence" / "logs" / "transitions.jsonl"
        assert log.exists(), "Audit log should exist after a rejected transition"

    def test_execute_logs_evidence(self, cat_root):
        exit_code, _, stderr = run_transition([
            "--execute", "--type", "mission", "--id", "MP-TEST-001",
            "--to", "blocked", "--reason", "logging test",
        ], cat_root)
        assert exit_code == 0, f"stderr: {stderr}"
        log = cat_root / "evidence" / "logs" / "transitions.jsonl"
        assert log.exists(), "Audit log should exist after execute"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:

    def test_mission_workflow_sequence(self, cat_root):
        # approved → dispatched → in_progress; none require evidence
        for to_state in ["dispatched", "in_progress"]:
            exit_code, _, stderr = run_transition([
                "--execute", "--type", "mission", "--id", "MP-TEST-001",
                "--to", to_state, "--reason", f"sequence test → {to_state}",
            ], cat_root)
            assert exit_code == 0, f"Failed → {to_state}. stderr: {stderr}"

    def test_bead_workflow_sequence(self, cat_root):
        # queued → active → in_progress; none require evidence
        for to_state in ["active", "in_progress"]:
            exit_code, _, stderr = run_transition([
                "--execute", "--type", "bead", "--id", "BEAD-TEST-001",
                "--to", to_state, "--reason", f"sequence test → {to_state}",
            ], cat_root)
            assert exit_code == 0, f"Failed → {to_state}. stderr: {stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
