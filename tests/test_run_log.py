"""Tests for scripts/cat_run_log.py — the AGENT_RUN_LOG.jsonl writer.

Drives ``main`` against temp paths (module-level path constants monkeypatched)
and verifies the schema header is written once and records are appended.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_run_log as rl  # noqa: E402


def test_git_head_short_returns_string():
    sha = rl._git_head_short()
    assert isinstance(sha, str)
    assert len(sha) >= 7


def test_read_tower_missing_file_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(rl, "_STATE_FILE", tmp_path / "absent.yaml")
    assert rl._read_tower() == {}


def test_read_tower_parses_yaml(monkeypatch, tmp_path):
    state = tmp_path / "TOWER_STATE.yaml"
    state.write_text("active_bead_id: BEAD-CAT-S001-4C01-01\n", encoding="utf-8")
    monkeypatch.setattr(rl, "_STATE_FILE", state)
    assert rl._read_tower()["active_bead_id"] == "BEAD-CAT-S001-4C01-01"


def _run(monkeypatch, tmp_path, extra_argv=()):
    log_path = tmp_path / "evidence" / "logs" / "AGENT_RUN_LOG.jsonl"
    monkeypatch.setattr(rl, "_LOG_PATH", log_path)
    monkeypatch.setattr(rl, "_STATE_FILE", tmp_path / "absent.yaml")
    argv = ["cat_run_log.py", "--confidence", "85", "--result", "did work", *extra_argv]
    monkeypatch.setattr(sys, "argv", argv)
    assert rl.main() == 0
    return log_path


def test_main_writes_header_and_record(monkeypatch, tmp_path):
    log_path = _run(monkeypatch, tmp_path, ["--files", "a.py, b.py", "--tools-used", "3"])
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    header = json.loads(lines[0])
    record = json.loads(lines[1])
    assert header["_schema"] == "AGENT_RUN_LOG v1"
    assert record["confidence_score"] == 85.0
    assert record["result"] == "did work"
    assert record["files_touched"] == ["a.py", "b.py"]
    assert record["tools_used"] == 3
    assert record["task_id"] == "unknown"  # no tower state


def test_main_appends_without_duplicate_header(monkeypatch, tmp_path):
    log_path = _run(monkeypatch, tmp_path)
    _run(monkeypatch, tmp_path)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    # one header + two records
    assert len(lines) == 3
    assert json.loads(lines[0])["_schema"] == "AGENT_RUN_LOG v1"
    assert json.loads(lines[1])["result"] == "did work"
    assert json.loads(lines[2])["result"] == "did work"
