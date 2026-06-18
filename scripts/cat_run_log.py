#!/usr/bin/env python3
"""
CAT Agent Run Log Writer.

Appends one JSON record to evidence/logs/AGENT_RUN_LOG.jsonl at the end of
a session, following the harness-v2 AGENT_RUN_LOG schema.

Usage:
    python scripts/cat_run_log.py \\
        --confidence 85 \\
        --result "closed BEAD-CAT-A007-4C01-01" \\
        --files "scripts/loghouse/normalize.py,tests/test_loghouse_engine.py" \\
        --validation "pytest -q passed" \\
        --next-task "BEAD-CAT-A007-4C01-02"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parent.parent

_LOG_PATH = ROOT / "evidence" / "logs" / "AGENT_RUN_LOG.jsonl"
_STATE_FILE = ROOT / "state" / "TOWER_STATE.yaml"
_SCHEMA_HEADER = {
    "_schema": "AGENT_RUN_LOG v1",
    "_fields": [
        "ts", "task_id", "model", "role", "confidence_score",
        "risk_level", "tools_used", "files_touched",
        "result", "validation", "next_task", "commit_sha",
    ],
    "_source": "cat_run_log.py",
}


def _git_head_short() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=ROOT, timeout=5,
        )
        sha = r.stdout.strip()
        return sha if len(sha) >= 7 else "0000000"
    except Exception:
        return "0000000"


def _read_tower() -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(_STATE_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Write one entry to AGENT_RUN_LOG.jsonl")
    parser.add_argument("--confidence", type=float, required=True, help="Confidence score 0–100")
    parser.add_argument("--result", required=True, help="Brief result description")
    parser.add_argument("--files", default="", help="Comma-separated list of files touched")
    parser.add_argument("--validation", default="", help="Validation command and outcome")
    parser.add_argument("--next-task", default="", help="Next BEAD or task ID")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model used this session")
    parser.add_argument("--role", default="worker", help="Agent role")
    parser.add_argument("--tools-used", type=int, default=0, help="Number of tool calls")
    parser.add_argument("--risk-level", default="", help="Risk level override")
    args = parser.parse_args()

    tower = _read_tower()
    task_id = tower.get("active_bead_id") or tower.get("active_mission_id") or "unknown"
    risk_level = args.risk_level or tower.get("control_planes", {}) and "medium" or "medium"

    files_touched = [f.strip() for f in args.files.split(",") if f.strip()]

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "model": args.model,
        "role": args.role,
        "confidence_score": args.confidence,
        "risk_level": risk_level,
        "tools_used": args.tools_used,
        "files_touched": files_touched,
        "result": args.result,
        "validation": args.validation,
        "next_task": args.next_task,
        "commit_sha": _git_head_short(),
    }

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write schema header if file is new or empty
    if not _LOG_PATH.exists() or _LOG_PATH.stat().st_size == 0:
        with _LOG_PATH.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_SCHEMA_HEADER) + "\n")

    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    print(f"[cat_run_log] Written to {_LOG_PATH}")
    print(f"  task_id:    {task_id}")
    print(f"  confidence: {args.confidence}")
    print(f"  result:     {args.result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
