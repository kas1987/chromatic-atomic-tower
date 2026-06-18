"""
CAT Self-Observability Adapter.

Reads CAT's operational JSONL logs and maps them to telemetry_envelope-compatible
dicts so they can be fed into the LOGHOUSE normalize → correlate → rules pipeline.

Field mapping convention (documented here, not in the schema):
  service    = "cat"
  env        = CAT_ENV env var ("local" | "ci"), default "local"
  commit_sha = git rev-parse HEAD at call time, or fallback "0000000"
  deploy_id  = active_sprint from state/TOWER_STATE.yaml, or fallback "SPRINT-000"

This makes sprint_id serve as the deployment context that groups all CAT governance
events into one correlation window.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

# Repo root resolution — works whether called as a module or directly.
_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[2]

_LOG_DIR = ROOT / "evidence" / "logs"
_STATE_FILE = ROOT / "state" / "TOWER_STATE.yaml"

CAT_SERVICE = "cat"


def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=ROOT, timeout=5,
        )
        sha = result.stdout.strip()
        return sha if len(sha) >= 7 else "0000000"
    except Exception:
        return "0000000"


def _active_sprint() -> str:
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(_STATE_FILE.read_text(encoding="utf-8"))
        sprint = data.get("active_sprint", "")
        return sprint if sprint else "SPRINT-000"
    except Exception:
        return "SPRINT-000"


def _env() -> str:
    return os.environ.get("CAT_ENV", "local")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines and schema-header lines."""
    if not path.exists():
        return []
    records = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Skip schema header lines (harness-v2 AGENT_RUN_LOG pattern)
            if "_schema" in obj or "_fields" in obj:
                continue
            records.append(obj)
    except OSError:
        pass
    return records


def _make_envelope(
    signal_type: str,
    ts: str,
    message: str,
    severity: str,
    attrs: dict[str, Any],
    commit_sha: str,
    deploy_id: str,
    env: str,
    event_id: str | None = None,
) -> dict[str, Any]:
    env_val: dict[str, Any] = {
        "signal_type": signal_type,
        "service": CAT_SERVICE,
        "env": env,
        "ts": ts,
        "message": message,
        "severity": severity,
        "commit_sha": commit_sha,
        "deploy_id": deploy_id,
        "attrs": attrs,
    }
    if event_id:
        env_val["event_id"] = event_id
    return env_val


def _adapt_transitions(records: list[dict], commit_sha: str, deploy_id: str, env: str) -> list[dict]:
    out = []
    for r in records:
        ts = r.get("timestamp") or r.get("ts", "1970-01-01T00:00:00+00:00")
        entity_id = r.get("entity_id", "unknown")
        from_state = r.get("from_state", "")
        to_state = r.get("to_state", "")
        message = f"BEAD {entity_id} transitioned {from_state} → {to_state}"
        attrs: dict[str, Any] = {
            "entity_id": entity_id,
            "entity_type": r.get("entity_type", "bead"),
            "from_state": from_state,
            "to_state": to_state,
            "event": r.get("event", ""),
        }
        out.append(_make_envelope(
            signal_type="bead_transition",
            ts=ts,
            message=message,
            severity="info",
            attrs=attrs,
            commit_sha=r.get("commit_sha", commit_sha),
            deploy_id=deploy_id,
            env=env,
        ))
    return out


def _adapt_closeouts(records: list[dict], commit_sha: str, deploy_id: str, env: str) -> list[dict]:
    out = []
    for r in records:
        ts = r.get("timestamp", "1970-01-01T00:00:00+00:00")
        allowed = r.get("allowed", True)
        target_id = r.get("target_id", "unknown")
        reason = r.get("reason", "")
        message = f"closeout {'allowed' if allowed else 'blocked'} for {target_id}: {reason}"
        severity = "error" if not allowed else "info"
        attrs: dict[str, Any] = {
            "target_id": target_id,
            "target_type": r.get("target_type", "bead"),
            "allowed": allowed,
            "reason": reason,
            "actor": r.get("actor", ""),
            "errors": r.get("errors", []),
        }
        out.append(_make_envelope(
            signal_type="closeout",
            ts=ts,
            message=message,
            severity=severity,
            attrs=attrs,
            commit_sha=commit_sha,
            deploy_id=deploy_id,
            env=env,
        ))
    return out


def _adapt_go_decisions(records: list[dict], commit_sha: str, deploy_id: str, env: str) -> list[dict]:
    out = []
    for r in records:
        ts = r.get("ts", "1970-01-01T00:00:00+00:00")
        allowed = r.get("allowed", True)
        drift_count = r.get("drift_count", 0)
        message = f"GO {'allowed' if allowed else 'blocked'} (drift_count={drift_count})"
        severity = "error" if not allowed else "info"
        attrs: dict[str, Any] = {
            "allowed": allowed,
            "drift_count": drift_count,
            "drifts": r.get("drifts", []),
            "sprint": r.get("sprint", ""),
        }
        out.append(_make_envelope(
            signal_type="go_decision",
            ts=ts,
            message=message,
            severity=severity,
            attrs=attrs,
            commit_sha=r.get("commit_sha", commit_sha),
            deploy_id=deploy_id,
            env=env,
        ))
    return out


def _adapt_agent_runs(records: list[dict], commit_sha: str, deploy_id: str, env: str) -> list[dict]:
    out = []
    for r in records:
        if "_schema" in r or "_fields" in r:
            continue
        ts = r.get("ts", "1970-01-01T00:00:00+00:00")
        confidence = float(r.get("confidence_score", 100))
        result = r.get("result", "")
        task_id = r.get("task_id", "unknown")
        message = f"agent run [{task_id}]: {result}"
        severity = "warn" if confidence < 70 else "info"
        attrs: dict[str, Any] = {
            "task_id": task_id,
            "model": r.get("model", ""),
            "role": r.get("role", "worker"),
            "confidence_score": confidence,
            "risk_level": r.get("risk_level", ""),
            "tools_used": r.get("tools_used", 0),
            "files_touched": r.get("files_touched", []),
            "result": result,
            "validation": r.get("validation", ""),
        }
        out.append(_make_envelope(
            signal_type="agent_run",
            ts=ts,
            message=message,
            severity=severity,
            attrs=attrs,
            commit_sha=r.get("commit_sha", commit_sha),
            deploy_id=deploy_id,
            env=env,
        ))
    return out


def load_cat_signals() -> list[dict[str, Any]]:
    """
    Read all CAT operational JSONL logs and return a list of raw signal dicts
    ready for normalize_batch().
    """
    commit_sha = _git_head()
    deploy_id = _active_sprint()
    env = _env()

    raw: list[dict[str, Any]] = []

    raw.extend(_adapt_transitions(
        _read_jsonl(_LOG_DIR.parent / "transitions" / "transition_log.jsonl"),
        commit_sha, deploy_id, env,
    ))
    raw.extend(_adapt_closeouts(
        _read_jsonl(_LOG_DIR / "closeouts.jsonl"),
        commit_sha, deploy_id, env,
    ))
    raw.extend(_adapt_go_decisions(
        _read_jsonl(_LOG_DIR / "go_decisions.jsonl"),
        commit_sha, deploy_id, env,
    ))
    raw.extend(_adapt_agent_runs(
        _read_jsonl(_LOG_DIR / "AGENT_RUN_LOG.jsonl"),
        commit_sha, deploy_id, env,
    ))

    return raw
