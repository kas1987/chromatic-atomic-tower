"""Unit tests for scripts/harness_bridge.py.

Exercises the pure helpers (outcome detection, queue lookup, bead-file
discovery, targeted status edits) and the evidence-report / durable-artifact
writers against temp directories. ``main`` is driven end-to-end against a
synthetic run folder with the module's ROOT-derived globals monkeypatched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import harness_bridge as hb


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def test_utc_stamp_format():
    stamp = hb.utc_stamp()
    assert stamp.endswith("Z")
    assert "T" in stamp
    assert len(stamp) == 20  # YYYY-MM-DDTHH:MM:SSZ


def test_read_text_missing_returns_empty(tmp_path):
    assert hb.read_text(tmp_path / "nope.txt") == ""


def test_read_text_reads_content(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("data", encoding="utf-8")
    assert hb.read_text(p) == "data"


# ---------------------------------------------------------------------------
# detect_outcome
# ---------------------------------------------------------------------------

def test_detect_outcome_from_review_packet_true(tmp_path):
    (tmp_path / "review_packet.md").write_text("Test passed: True\n", encoding="utf-8")
    passed, rationale = hb.detect_outcome(tmp_path)
    assert passed is True
    assert "review_packet" in rationale


def test_detect_outcome_from_review_packet_false(tmp_path):
    (tmp_path / "review_packet.md").write_text("Test passed: False\n", encoding="utf-8")
    passed, _ = hb.detect_outcome(tmp_path)
    assert passed is False


def test_detect_outcome_falls_back_to_test_output_pass(tmp_path):
    (tmp_path / "test_output.txt").write_text("14 passed in 0.03s\n", encoding="utf-8")
    passed, rationale = hb.detect_outcome(tmp_path)
    assert passed is True
    assert "test_output" in rationale


def test_detect_outcome_test_output_failure(tmp_path):
    (tmp_path / "test_output.txt").write_text("1 failed, 2 passed\n", encoding="utf-8")
    passed, _ = hb.detect_outcome(tmp_path)
    assert passed is False


def test_detect_outcome_no_evidence_defaults_false(tmp_path):
    passed, rationale = hb.detect_outcome(tmp_path)
    assert passed is False
    assert "no conclusive evidence" in rationale


# ---------------------------------------------------------------------------
# find_queue_item
# ---------------------------------------------------------------------------

def test_find_queue_item_by_ticket():
    queue = {"items": [{"id": "DEMO-1"}, {"id": "DEMO-2", "bead_id": "B-2"}]}
    assert hb.find_queue_item(queue, ticket="DEMO-2", bead="B-2")["id"] == "DEMO-2"


def test_find_queue_item_by_bead_when_no_ticket():
    queue = {"items": [{"id": "DEMO-1", "bead_id": "B-9"}]}
    assert hb.find_queue_item(queue, ticket=None, bead="B-9")["id"] == "DEMO-1"


def test_find_queue_item_none_when_absent():
    assert hb.find_queue_item({"items": []}, ticket="X", bead="Y") is None


# ---------------------------------------------------------------------------
# load_queue
# ---------------------------------------------------------------------------

def test_load_queue_reads(monkeypatch, tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text(json.dumps({"items": [{"id": "Q"}]}), encoding="utf-8")
    monkeypatch.setattr(hb, "QUEUE_PATH", qp)
    assert hb.load_queue() == {"items": [{"id": "Q"}]}


def test_load_queue_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(hb, "QUEUE_PATH", tmp_path / "absent.json")
    assert hb.load_queue() == {}


# ---------------------------------------------------------------------------
# find_bead_file / update_bead_status
# ---------------------------------------------------------------------------

def test_find_bead_file_locates_in_active(monkeypatch, tmp_path):
    active = tmp_path / "beads" / "active"
    active.mkdir(parents=True)
    bead = active / "BEAD-CAT-S001-4C01-01.yaml"
    bead.write_text("status: active\n", encoding="utf-8")
    monkeypatch.setattr(hb, "ROOT", tmp_path)
    found = hb.find_bead_file("BEAD-CAT-S001-4C01-01")
    assert found == bead


def test_find_bead_file_returns_none_when_missing(monkeypatch, tmp_path):
    (tmp_path / "beads" / "active").mkdir(parents=True)
    monkeypatch.setattr(hb, "ROOT", tmp_path)
    assert hb.find_bead_file("BEAD-NOPE") is None


def test_update_bead_status_changes_line(tmp_path):
    bead = tmp_path / "b.yaml"
    bead.write_text("bead_id: X\nstatus: active\ntitle: T\n", encoding="utf-8")
    old, changed = hb.update_bead_status(bead, "validating")
    assert old == "active"
    assert changed is True
    assert "status: validating" in bead.read_text(encoding="utf-8")


def test_update_bead_status_noop_when_same(tmp_path):
    bead = tmp_path / "b.yaml"
    bead.write_text("status: validating\n", encoding="utf-8")
    old, changed = hb.update_bead_status(bead, "validating")
    assert changed is False
    assert old == "validating"


# ---------------------------------------------------------------------------
# copy_durable_artifacts
# ---------------------------------------------------------------------------

def test_copy_durable_artifacts(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "review_packet.md").write_text("packet", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("out", encoding="utf-8")
    (run_dir / "ignored.txt").write_text("nope", encoding="utf-8")
    monkeypatch.setattr(hb, "EVIDENCE_RUNS_DIR", tmp_path / "evidence" / "runs")
    dest = hb.copy_durable_artifacts(run_dir, "DEMO-1")
    assert (dest / "review_packet.md").read_text(encoding="utf-8") == "packet"
    assert (dest / "test_output.txt").read_text(encoding="utf-8") == "out"
    assert not (dest / "ignored.txt").exists()


# ---------------------------------------------------------------------------
# write_evidence_report
# ---------------------------------------------------------------------------

def test_write_evidence_report(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "git_diff_names.txt").write_text("scripts/x.py\n", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("3 passed\n", encoding="utf-8")
    monkeypatch.setattr(hb, "REPORTS_DIR", tmp_path / "evidence" / "reports")
    monkeypatch.setattr(hb, "ROOT", tmp_path)
    out = hb.write_evidence_report(
        bead_id="BEAD-CAT-S001-4C01-01", ticket="DEMO-1", run_dir=run_dir,
        passed=True, rationale="test_output.txt shows only passes",
        bead_status_change="active -> validating", queue_status="review",
    )
    body = out.read_text(encoding="utf-8")
    assert "Evidence Report: BEAD-CAT-S001-4C01-01" in body
    assert "passed" in body
    assert "scripts/x.py" in body
    assert "3 passed" in body


# ---------------------------------------------------------------------------
# main — end-to-end against a synthetic run folder
# ---------------------------------------------------------------------------

def _setup_root(monkeypatch, tmp_path):
    agent = tmp_path / ".agent"
    run_dir = agent / "runs" / "DEMO-1"
    run_dir.mkdir(parents=True)
    (run_dir / "review_packet.md").write_text("Test passed: True\n", encoding="utf-8")
    (run_dir / "test_output.txt").write_text("5 passed\n", encoding="utf-8")
    queue = agent / "queue.json"
    queue.write_text(
        json.dumps({"items": [{"id": "DEMO-1", "bead_id": "BEAD-CAT-S001-4C01-01"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb, "ROOT", tmp_path)
    monkeypatch.setattr(hb, "AGENT_DIR", agent)
    monkeypatch.setattr(hb, "QUEUE_PATH", queue)
    monkeypatch.setattr(hb, "REPORTS_DIR", tmp_path / "evidence" / "reports")
    monkeypatch.setattr(hb, "EVIDENCE_RUNS_DIR", tmp_path / "evidence" / "runs")
    return agent, run_dir, queue


def test_main_no_bead_update_path(monkeypatch, tmp_path):
    agent, run_dir, queue = _setup_root(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", [
        "harness_bridge.py", "--bead", "BEAD-CAT-S001-4C01-01",
        "--ticket", "DEMO-1", "--no-bead-update",
    ])
    rc = hb.main()
    assert rc == 0
    # queue advanced to review
    data = json.loads(queue.read_text(encoding="utf-8"))
    assert data["items"][0]["status"] == "review"
    # evidence report written
    assert (tmp_path / "evidence" / "reports" / "BEAD-CAT-S001-4C01-01_harness_run.md").exists()
    # durable artifacts copied
    assert (tmp_path / "evidence" / "runs" / "DEMO-1" / "review_packet.md").exists()


def test_main_errors_when_run_folder_missing(monkeypatch, tmp_path):
    agent, run_dir, queue = _setup_root(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", [
        "harness_bridge.py", "--bead", "B", "--ticket", "MISSING", "--no-bead-update",
    ])
    assert hb.main() == 2


def test_main_errors_when_ticket_unresolvable(monkeypatch, tmp_path):
    agent, run_dir, queue = _setup_root(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.argv", [
        "harness_bridge.py", "--bead", "BEAD-UNLINKED", "--no-bead-update",
    ])
    assert hb.main() == 2
