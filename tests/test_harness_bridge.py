"""
tests/test_harness_bridge.py

Comprehensive tests for scripts/harness_bridge.py.

All tests use tmp_path for filesystem isolation and set CAT_ROOT via
monkeypatch so that common.ROOT (and all derived paths in harness_bridge)
resolve through the temporary fixture rather than the live repo.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# ---------------------------------------------------------------------------
# We need to import harness_bridge with a controlled CAT_ROOT.
# The module is re-loaded per test via a fresh import after monkeypatching the
# env var is not straightforward — instead we import the module once and patch
# its module-level attributes in each test using monkeypatch/patch.
# ---------------------------------------------------------------------------
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import harness_bridge


# ---------------------------------------------------------------------------
# Minimal BEAD YAML that passes the schema
# ---------------------------------------------------------------------------

_VALID_BEAD_YAML = textwrap.dedent("""\
    bead_id: BEAD-TEST-001
    mission_id: MP-TEST-001
    title: Test BEAD for bridge
    status: in_progress
    agent_role: Builder
    autonomy_level: L3
    objective: This is a test objective with enough length.
    allowed_paths:
      - scripts/**
    forbidden_paths:
      - .env
    tool_budget:
      search: 5
      read: 10
      write: 5
      execute: 3
      max_runtime_minutes: 30
    confidence:
      minimum: 75
      current: 80
      objective_clarity: 80
      scope_clarity: 80
      evidence_quality: 80
      reversibility: 90
      tool_fit: 80
      risk_awareness: 80
      testability: 80
    risk_level: low
    reversibility: high
    stop_conditions:
      - Tests fail three times.
    definition_of_done:
      - All tests pass.
    validation:
      - type: tests
        command: pytest -q
        evidence_path: evidence/test-results/out.txt
        required: true
    required_output:
      - summary
    handoff:
      next_bead_id: null
      notes: []
""")


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------

def _make_run_dir(
    tmp_path: Path,
    ticket: str = "TEST-001",
    test_passed: bool = True,
    test_output: str | None = None,
) -> Path:
    """
    Create a minimal .agent/runs/<ticket>/ directory that harness_bridge reads.
    Returns the run_dir path.
    """
    agent_dir = tmp_path / ".agent"
    run_dir = agent_dir / "runs" / ticket
    run_dir.mkdir(parents=True, exist_ok=True)

    if test_output is None:
        test_output = "5 passed in 0.03s" if test_passed else "1 failed, 2 passed in 0.05s"

    result_line = f"Test passed: {test_passed}"
    packet = textwrap.dedent(f"""\
        # Review Packet

        ## Ticket

        Ticket content here.

        ## Test Results

        ```text
        {test_output}
        ```

        ## Worker Self-Assessment

        Worker model: test-model
        Attempts used: 1 / 2
        Files written: ['scripts/harness_demo.py']
        Guardrail violations: []
        Escalation notes: []

        ## Known Failures / Exceptions

        {result_line}
        Guardrail violations: None
        Escalation notes: None
    """)

    (run_dir / "review_packet.md").write_text(packet, encoding="utf-8")
    (run_dir / "test_output.txt").write_text(test_output, encoding="utf-8")
    (run_dir / "git_diff_names.txt").write_text("scripts/harness_demo.py\n", encoding="utf-8")
    (run_dir / "git_diff_full.txt").write_text("diff --git a/scripts/harness_demo.py...\n", encoding="utf-8")
    (run_dir / "git_diff_stat.txt").write_text(" scripts/harness_demo.py | 10 ++++------\n", encoding="utf-8")
    (run_dir / "worker_response.md").write_text("# Worker response\nHere is my solution.\n", encoding="utf-8")
    (run_dir / "cheap_review.md").write_text("LGTM.\n", encoding="utf-8")

    return run_dir


def _make_queue(
    tmp_path: Path,
    items: list[dict] | None = None,
) -> Path:
    """Write a queue.json and return its path."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    q_path = agent_dir / "queue.json"
    if items is None:
        items = [{"id": "TEST-001", "status": "pending", "bead_id": "BEAD-TEST-001"}]
    q_path.write_text(json.dumps({"items": items}), encoding="utf-8")
    return q_path


def _make_bead_file(
    tmp_path: Path,
    bead_id: str = "BEAD-TEST-001",
    status: str = "in_progress",
    directory: str = "beads/active",
    content: str | None = None,
) -> Path:
    bead_dir = tmp_path / directory
    bead_dir.mkdir(parents=True, exist_ok=True)
    bead_path = bead_dir / f"{bead_id}.yaml"
    if content is None:
        content = _VALID_BEAD_YAML.replace("in_progress", status, 1)
    bead_path.write_text(content, encoding="utf-8")
    return bead_path


# ---------------------------------------------------------------------------
# detect_outcome
# ---------------------------------------------------------------------------

def test_detect_outcome_pass_from_review_packet(tmp_path):
    run_dir = _make_run_dir(tmp_path, test_passed=True)
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is True
    assert "review_packet" in rationale


def test_detect_outcome_fail_from_review_packet(tmp_path):
    run_dir = _make_run_dir(tmp_path, test_passed=False)
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is False
    assert "review_packet" in rationale


def test_detect_outcome_fallback_to_test_output_pass(tmp_path):
    """When review_packet has no 'Test passed:' line, fall back to test_output.txt."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review_packet.md").write_text("# No outcome line\n", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("14 passed in 0.10s\n", encoding="utf-8")
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is True
    assert "test_output.txt" in rationale


def test_detect_outcome_fallback_to_test_output_fail(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review_packet.md").write_text("# No outcome line\n", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("2 failed, 5 passed in 0.50s\n", encoding="utf-8")
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is False
    assert "test_output.txt" in rationale


def test_detect_outcome_no_files_defaults_to_fail(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is False
    assert "no conclusive evidence" in rationale


def test_detect_outcome_error_in_test_output(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review_packet.md").write_text("No outcome\n", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("ERROR: module not found\n", encoding="utf-8")
    passed, rationale = harness_bridge.detect_outcome(run_dir)
    assert passed is False


# ---------------------------------------------------------------------------
# read_text
# ---------------------------------------------------------------------------

def test_bridge_read_text_existing(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello", encoding="utf-8")
    assert harness_bridge.read_text(p) == "hello"


def test_bridge_read_text_missing(tmp_path):
    assert harness_bridge.read_text(tmp_path / "nonexistent.txt") == ""


# ---------------------------------------------------------------------------
# load_queue
# ---------------------------------------------------------------------------

def test_load_queue_valid(tmp_path, monkeypatch):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"items": [{"id": "T-001"}]}), encoding="utf-8")
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q)
    result = harness_bridge.load_queue()
    assert result["items"][0]["id"] == "T-001"


def test_load_queue_corrupt_returns_empty(tmp_path, monkeypatch):
    q = tmp_path / "queue.json"
    q.write_text("NOT JSON {{", encoding="utf-8")
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q)
    result = harness_bridge.load_queue()
    assert result == {}


def test_load_queue_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", tmp_path / "no_queue.json")
    result = harness_bridge.load_queue()
    assert result == {}


# ---------------------------------------------------------------------------
# find_queue_item
# ---------------------------------------------------------------------------

def test_find_queue_item_by_ticket():
    queue = {"items": [{"id": "T-001", "bead_id": "B-1"}, {"id": "T-002", "bead_id": "B-2"}]}
    item = harness_bridge.find_queue_item(queue, ticket="T-001", bead="B-99")
    assert item["id"] == "T-001"


def test_find_queue_item_by_bead_fallback():
    queue = {"items": [{"id": "T-001", "bead_id": "BEAD-MATCH"}]}
    item = harness_bridge.find_queue_item(queue, ticket=None, bead="BEAD-MATCH")
    assert item["bead_id"] == "BEAD-MATCH"


def test_find_queue_item_not_found():
    queue = {"items": [{"id": "T-001", "bead_id": "B-1"}]}
    assert harness_bridge.find_queue_item(queue, ticket="NONE", bead="NONE") is None


def test_find_queue_item_empty_queue():
    assert harness_bridge.find_queue_item({}, ticket="T-1", bead="B-1") is None


# ---------------------------------------------------------------------------
# find_bead_file
# ---------------------------------------------------------------------------

def test_find_bead_file_in_active(tmp_path, monkeypatch):
    bead_path = _make_bead_file(tmp_path, "BEAD-FIND-001", directory="beads/active")
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    found = harness_bridge.find_bead_file("BEAD-FIND-001")
    assert found == bead_path


def test_find_bead_file_in_examples(tmp_path, monkeypatch):
    bead_path = _make_bead_file(tmp_path, "BEAD-EX-001", directory="beads/examples")
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    found = harness_bridge.find_bead_file("BEAD-EX-001")
    assert found == bead_path


def test_find_bead_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    (tmp_path / "beads" / "active").mkdir(parents=True, exist_ok=True)
    (tmp_path / "beads" / "examples").mkdir(parents=True, exist_ok=True)
    assert harness_bridge.find_bead_file("BEAD-MISSING-999") is None


# ---------------------------------------------------------------------------
# update_bead_status
# ---------------------------------------------------------------------------

def test_update_bead_status_changes_status(tmp_path):
    bead_path = _make_bead_file(tmp_path, status="in_progress")
    old, changed = harness_bridge.update_bead_status(bead_path, "validating")
    assert old == "in_progress"
    assert changed is True
    assert "status: validating" in bead_path.read_text(encoding="utf-8")


def test_update_bead_status_no_change_same_status(tmp_path):
    bead_path = _make_bead_file(tmp_path, status="validating")
    old, changed = harness_bridge.update_bead_status(bead_path, "validating")
    assert old == "validating"
    assert changed is False


def test_update_bead_status_preserves_other_fields(tmp_path):
    bead_path = _make_bead_file(tmp_path, status="in_progress")
    harness_bridge.update_bead_status(bead_path, "blocked")
    content = bead_path.read_text(encoding="utf-8")
    assert "bead_id: BEAD-TEST-001" in content
    assert "mission_id: MP-TEST-001" in content


# ---------------------------------------------------------------------------
# bead_is_valid (uses the real schema from the repo)
# ---------------------------------------------------------------------------

def test_bead_is_valid_with_good_yaml(tmp_path, monkeypatch):
    bead_path = _make_bead_file(tmp_path, status="validating")
    monkeypatch.setattr(harness_bridge, "BEAD_SCHEMA", ROOT / "schemas" / "bead.schema.json")
    errors = harness_bridge.bead_is_valid(bead_path)
    assert errors == [], f"Expected no errors but got: {errors}"


def test_bead_is_valid_invalid_status(tmp_path, monkeypatch):
    bead_path = _make_bead_file(tmp_path, status="INVALID_STATUS")
    monkeypatch.setattr(harness_bridge, "BEAD_SCHEMA", ROOT / "schemas" / "bead.schema.json")
    errors = harness_bridge.bead_is_valid(bead_path)
    assert errors  # should have validation errors


# ---------------------------------------------------------------------------
# copy_durable_artifacts
# ---------------------------------------------------------------------------

def test_copy_durable_artifacts_copies_all_expected_files(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_bridge, "EVIDENCE_RUNS_DIR", tmp_path / "evidence" / "runs")
    run_dir = _make_run_dir(tmp_path)
    dest = harness_bridge.copy_durable_artifacts(run_dir, "TEST-001")
    assert (dest / "review_packet.md").exists()
    assert (dest / "test_output.txt").exists()
    assert (dest / "worker_response.md").exists()
    assert (dest / "cheap_review.md").exists()


def test_copy_durable_artifacts_skips_missing_files(tmp_path, monkeypatch):
    """copy_durable_artifacts shouldn't fail if some artifacts are missing."""
    monkeypatch.setattr(harness_bridge, "EVIDENCE_RUNS_DIR", tmp_path / "evidence" / "runs")
    run_dir = tmp_path / ".agent" / "runs" / "SPARSE-001"
    run_dir.mkdir(parents=True)
    # Only write one artifact
    (run_dir / "test_output.txt").write_text("3 passed\n", encoding="utf-8")
    dest = harness_bridge.copy_durable_artifacts(run_dir, "SPARSE-001")
    assert (dest / "test_output.txt").exists()
    # No error even though most files are missing
    assert not (dest / "review_packet.md").exists()


# ---------------------------------------------------------------------------
# write_evidence_report
# ---------------------------------------------------------------------------

def test_write_evidence_report_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_bridge, "REPORTS_DIR", tmp_path / "evidence" / "reports")
    run_dir = _make_run_dir(tmp_path)
    report = harness_bridge.write_evidence_report(
        bead_id="BEAD-TEST-001",
        ticket="TEST-001",
        run_dir=run_dir,
        passed=True,
        rationale="review_packet.md",
        bead_status_change="in_progress -> validating",
        queue_status="review",
    )
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "BEAD-TEST-001" in content
    assert "TEST-001" in content
    assert "passed" in content


def test_write_evidence_report_fail_outcome(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_bridge, "REPORTS_DIR", tmp_path / "evidence" / "reports")
    run_dir = _make_run_dir(tmp_path, test_passed=False)
    report = harness_bridge.write_evidence_report(
        bead_id="BEAD-TEST-001",
        ticket="TEST-001",
        run_dir=run_dir,
        passed=False,
        rationale="test_output.txt shows failures",
        bead_status_change="in_progress -> blocked",
        queue_status="blocked",
    )
    content = report.read_text(encoding="utf-8")
    assert "failed" in content
    assert "blocked" in content


def test_write_evidence_report_truncates_long_test_output(tmp_path, monkeypatch):
    """Test output longer than 4000 chars should be truncated in the report."""
    monkeypatch.setattr(harness_bridge, "REPORTS_DIR", tmp_path / "evidence" / "reports")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    long_output = "line\n" * 2000  # >> 4000 chars
    (run_dir / "test_output.txt").write_text(long_output, encoding="utf-8")
    (run_dir / "git_diff_names.txt").write_text("scripts/foo.py\n", encoding="utf-8")
    report = harness_bridge.write_evidence_report(
        bead_id="BEAD-TEST-001",
        ticket="TEST-001",
        run_dir=run_dir,
        passed=True,
        rationale="mock",
        bead_status_change="in_progress -> validating",
        queue_status="review",
    )
    content = report.read_text(encoding="utf-8")
    # The file exists; we just verify it was created without error
    assert report.exists()
    # Verify output is truncated — 2000 "line\n" = 10000 chars, report must be well under that
    assert len(content) < 6000


# ---------------------------------------------------------------------------
# utc_stamp
# ---------------------------------------------------------------------------

def test_utc_stamp_format():
    stamp = harness_bridge.utc_stamp()
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp)


# ---------------------------------------------------------------------------
# main() — end-to-end via direct call with monkeypatching
# ---------------------------------------------------------------------------

def _setup_bridge_env(
    tmp_path: Path,
    monkeypatch,
    *,
    ticket: str = "TEST-001",
    bead_id: str = "BEAD-TEST-001",
    test_passed: bool = True,
    queue_items: list[dict] | None = None,
    bead_status: str = "in_progress",
    create_bead: bool = True,
) -> dict:
    """
    Build a complete self-contained environment for main() to run.
    Returns a dict of key paths.
    """
    agent_dir = tmp_path / ".agent"
    run_dir = _make_run_dir(tmp_path, ticket=ticket, test_passed=test_passed)

    if queue_items is None:
        queue_items = [{"id": ticket, "status": "pending", "bead_id": bead_id}]
    q_path = _make_queue(tmp_path, queue_items)

    bead_path = None
    if create_bead:
        bead_path = _make_bead_file(tmp_path, bead_id=bead_id, status=bead_status)

    reports_dir = tmp_path / "evidence" / "reports"
    evidence_runs_dir = tmp_path / "evidence" / "runs"

    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    monkeypatch.setattr(harness_bridge, "AGENT_DIR", agent_dir)
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q_path)
    monkeypatch.setattr(harness_bridge, "BEAD_SCHEMA", ROOT / "schemas" / "bead.schema.json")
    monkeypatch.setattr(harness_bridge, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_bridge, "EVIDENCE_RUNS_DIR", evidence_runs_dir)

    return {
        "agent_dir": agent_dir,
        "run_dir": run_dir,
        "q_path": q_path,
        "bead_path": bead_path,
        "reports_dir": reports_dir,
    }


def test_main_pass_updates_queue_to_review(tmp_path, monkeypatch):
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    assert result == 0
    q = json.loads(paths["q_path"].read_text())
    item = next((i for i in q["items"] if i["id"] == "TEST-001"), None)
    assert item is not None
    assert item["status"] == harness_bridge.PASS_QUEUE_STATUS


def test_main_fail_updates_queue_to_blocked(tmp_path, monkeypatch):
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=False)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    assert result == 0
    q = json.loads(paths["q_path"].read_text())
    item = next((i for i in q["items"] if i["id"] == "TEST-001"), None)
    assert item["status"] == harness_bridge.FAIL_QUEUE_STATUS


def test_main_pass_sets_bead_to_validating(tmp_path, monkeypatch):
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        harness_bridge.main()

    bead_content = paths["bead_path"].read_text(encoding="utf-8")
    assert "status: validating" in bead_content


def test_main_fail_sets_bead_to_blocked(tmp_path, monkeypatch):
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=False)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        harness_bridge.main()

    bead_content = paths["bead_path"].read_text(encoding="utf-8")
    assert "status: blocked" in bead_content


def test_main_no_bead_update_flag(tmp_path, monkeypatch):
    """--no-bead-update should leave the BEAD file unchanged."""
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)
    before = paths["bead_path"].read_text(encoding="utf-8")

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001",
                             "--ticket", "TEST-001", "--no-bead-update"]):
        harness_bridge.main()

    assert paths["bead_path"].read_text(encoding="utf-8") == before


def test_main_creates_evidence_report(tmp_path, monkeypatch):
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        harness_bridge.main()

    report = paths["reports_dir"] / "BEAD-TEST-001_harness_run.md"
    assert report.exists()


def test_main_missing_run_dir_returns_2(tmp_path, monkeypatch):
    """If the run folder doesn't exist, main() should return exit code 2."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    q_path = _make_queue(tmp_path)
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    monkeypatch.setattr(harness_bridge, "AGENT_DIR", agent_dir)
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q_path)

    # No run directory created
    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    assert result == 2


def test_main_resolves_ticket_from_queue_by_bead_id(tmp_path, monkeypatch):
    """When --ticket is omitted, ticket should be resolved via bead_id in queue.json."""
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    # Don't supply --ticket; it should be resolved from queue's bead_id
    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001"]):
        result = harness_bridge.main()

    assert result == 0


def test_main_no_ticket_and_bead_not_in_queue_returns_2(tmp_path, monkeypatch):
    """If ticket can't be resolved from queue, return 2."""
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir(parents=True)
    # Queue with no matching bead_id
    q_path = _make_queue(tmp_path, [{"id": "OTHER-001", "status": "pending", "bead_id": "BEAD-OTHER"}])
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    monkeypatch.setattr(harness_bridge, "AGENT_DIR", agent_dir)
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q_path)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001"]):
        result = harness_bridge.main()

    assert result == 2


def test_main_bead_file_not_found_skips_bead_update(tmp_path, monkeypatch):
    """When bead file doesn't exist, bead update is skipped; rest still succeeds."""
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True, create_bead=False)
    (tmp_path / "beads" / "active").mkdir(parents=True, exist_ok=True)
    (tmp_path / "beads" / "examples").mkdir(parents=True, exist_ok=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    # Should still succeed (bead update is a best-effort step)
    assert result == 0


def test_main_bead_reverted_on_schema_invalid(tmp_path, monkeypatch):
    """If editing the BEAD makes it schema-invalid, the edit is reverted."""
    # Use a minimal bead that will fail schema validation after status change
    # by corrupting the bead schema path
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    # Point to a schema that rejects everything
    bogus_schema = tmp_path / "bogus_schema.json"
    bogus_schema.write_text(json.dumps({"type": "null"}), encoding="utf-8")
    monkeypatch.setattr(harness_bridge, "BEAD_SCHEMA", bogus_schema)

    before = paths["bead_path"].read_text(encoding="utf-8")

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    # Should still complete (schema failures only trigger a revert, not a crash)
    assert result == 0
    # BEAD should be reverted to original status
    after = paths["bead_path"].read_text(encoding="utf-8")
    assert "status: in_progress" in after


def test_main_copies_artifacts_to_evidence_runs(tmp_path, monkeypatch):
    """After main(), artifacts should appear in evidence/runs/<ticket>/."""
    paths = _setup_bridge_env(tmp_path, monkeypatch, test_passed=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        harness_bridge.main()

    evidence_run_dir = tmp_path / "evidence" / "runs" / "TEST-001"
    assert evidence_run_dir.exists()
    assert (evidence_run_dir / "review_packet.md").exists()
    assert (evidence_run_dir / "test_output.txt").exists()


def test_main_queue_item_gets_bead_id_set(tmp_path, monkeypatch):
    """If queue item lacks bead_id, main() should set it."""
    queue_items = [{"id": "TEST-001", "status": "pending"}]  # no bead_id
    paths = _setup_bridge_env(tmp_path, monkeypatch, queue_items=queue_items, test_passed=True)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        harness_bridge.main()

    q = json.loads(paths["q_path"].read_text())
    item = next(i for i in q["items"] if i["id"] == "TEST-001")
    assert item.get("bead_id") == "BEAD-TEST-001"


def test_main_corrupt_queue_still_creates_report(tmp_path, monkeypatch):
    """Even with a corrupt queue.json, the evidence report should still be written."""
    _make_run_dir(tmp_path, test_passed=True)
    q_path = tmp_path / ".agent" / "queue.json"
    q_path.write_text("CORRUPT {{{", encoding="utf-8")
    _make_bead_file(tmp_path, "BEAD-TEST-001")

    reports_dir = tmp_path / "evidence" / "reports"
    evidence_runs_dir = tmp_path / "evidence" / "runs"
    monkeypatch.setattr(harness_bridge, "ROOT", tmp_path)
    monkeypatch.setattr(harness_bridge, "AGENT_DIR", tmp_path / ".agent")
    monkeypatch.setattr(harness_bridge, "QUEUE_PATH", q_path)
    monkeypatch.setattr(harness_bridge, "BEAD_SCHEMA", ROOT / "schemas" / "bead.schema.json")
    monkeypatch.setattr(harness_bridge, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_bridge, "EVIDENCE_RUNS_DIR", evidence_runs_dir)

    with patch("sys.argv", ["harness_bridge.py", "--bead", "BEAD-TEST-001", "--ticket", "TEST-001"]):
        result = harness_bridge.main()

    assert result == 0
    report = reports_dir / "BEAD-TEST-001_harness_run.md"
    assert report.exists()
