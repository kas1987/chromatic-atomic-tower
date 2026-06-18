"""
LOGHOUSE Agent Observability (agent_obs.py)

Maps a local agent run trace (a dict with steps/tool calls) into
telemetry_envelope-valid records (signal_type "event" or "trace"),
and supports an agent-drift finding category.

The finding.schema.json category enum includes "aiops" and "drift";
agent-drift findings use category "aiops" — the schema is NOT modified.

Usage:
    from scripts.loghouse.agent_obs import trace_to_envelopes, detect_agent_drift

    envelopes = trace_to_envelopes(agent_trace)
    finding = detect_agent_drift(agent_trace, envelopes)
"""

from __future__ import annotations

import uuid
from typing import Any

from scripts.common import ROOT, validate_with_schema

ENVELOPE_SCHEMA = ROOT / "schemas" / "telemetry_envelope.schema.json"
FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"

# Anomaly thresholds for agent-drift detection
MAX_TOOL_CALLS_PER_STEP = 20
MAX_STEPS = 50
FORBIDDEN_TOOL_PATTERNS = frozenset(["rm -rf", "drop table", "delete from", "format c:"])


def trace_to_envelopes(
    agent_trace: dict[str, Any],
    *,
    service: str | None = None,
    env: str = "dev",
    deploy_id: str | None = None,
    commit_sha: str | None = None,
) -> list[dict[str, Any]]:
    """
    Map a local agent run trace into telemetry_envelope-valid records.

    The input ``agent_trace`` is a dict with the following shape (all optional
    except ``run_id`` and ``steps``):

        {
            "run_id": "run-abc123",           # used as deploy_id
            "agent": "BUILDER",               # used as service name
            "commit_sha": "abc1234",
            "started_at": "2026-06-17T12:00:00Z",
            "steps": [
                {
                    "step_id": "step-001",
                    "ts": "2026-06-17T12:00:01Z",
                    "tool": "Read",
                    "input": {"file_path": "/some/file.py"},
                    "output_summary": "read 100 lines",
                    "duration_ms": 120,
                },
                ...
            ],
        }

    Each step emits one telemetry_envelope record with signal_type "event"
    (for single tool invocations) or "trace" (if the step has a trace_id).

    Returns a list of validated telemetry_envelope records (invalid ones are
    silently dropped with a warning).
    """
    run_id = agent_trace.get("run_id", str(uuid.uuid4()))
    agent_name = service or agent_trace.get("agent", "unknown-agent")
    sha = commit_sha or agent_trace.get("commit_sha", "0000000")
    did = deploy_id or run_id

    envelopes: list[dict[str, Any]] = []

    for step in agent_trace.get("steps", []):
        step_id = step.get("step_id", str(uuid.uuid4()))
        ts = step.get("ts", "1970-01-01T00:00:00Z")
        tool = step.get("tool", "unknown")
        output_summary = step.get("output_summary", "")
        trace_id = step.get("trace_id", "")
        signal_type = "trace" if trace_id else "event"

        attrs: dict[str, Any] = {
            "tool": tool,
            "duration_ms": step.get("duration_ms", 0),
        }
        if step.get("input"):
            # Truncate large inputs
            input_str = str(step["input"])[:200]
            attrs["input_summary"] = input_str

        record: dict[str, Any] = {
            "event_id": step_id,
            "ts": ts,
            "signal_type": signal_type,
            "service": agent_name,
            "env": env,
            "severity": "info",
            "message": f"[agent] {tool}: {output_summary}"[:256],
            "commit_sha": sha,
            "deploy_id": did,
            "attrs": attrs,
        }
        if trace_id:
            record["trace_id"] = trace_id

        errors = validate_with_schema(record, ENVELOPE_SCHEMA)
        if errors:
            print(f"[agent_obs] SKIP step {step_id} — envelope schema errors: {errors}")
            continue

        envelopes.append(record)

    return envelopes


def detect_agent_drift(
    agent_trace: dict[str, Any],
    envelopes: list[dict[str, Any]],
    *,
    finding_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Detect anomalies in an agent run trace and emit an agent-drift finding.

    Anomaly signals:
    - Too many steps (> MAX_STEPS)
    - A step with too many tool calls (> MAX_TOOL_CALLS_PER_STEP)
    - Forbidden tool invocation patterns (destructive commands)

    If no anomaly is detected, returns None.

    The finding uses category "aiops" (within the existing finding.schema.json enum).
    """
    steps = agent_trace.get("steps", [])
    run_id = agent_trace.get("run_id", "unknown-run")
    agent_name = agent_trace.get("agent", "unknown-agent")
    started_at = agent_trace.get("started_at", "1970-01-01T00:00:00Z")

    anomalies: list[dict[str, Any]] = []

    # Check: too many steps
    if len(steps) > MAX_STEPS:
        anomalies.append({
            "type": "step_overflow",
            "detail": f"Agent ran {len(steps)} steps (max={MAX_STEPS}); possible runaway loop.",
            "step_id": None,
        })

    # Check: forbidden tool patterns
    for step in steps:
        tool = step.get("tool", "")
        input_str = str(step.get("input", "")).lower()
        for pattern in FORBIDDEN_TOOL_PATTERNS:
            if pattern in input_str:
                anomalies.append({
                    "type": "forbidden_tool_pattern",
                    "detail": f"Step {step.get('step_id', '?')} invoked tool '{tool}' "
                              f"with forbidden pattern '{pattern}'.",
                    "step_id": step.get("step_id"),
                })

        # Check: too many tool calls in a single step (multi-call batching abuse)
        tool_calls = step.get("tool_calls", [])
        if isinstance(tool_calls, list) and len(tool_calls) > MAX_TOOL_CALLS_PER_STEP:
            anomalies.append({
                "type": "tool_call_burst",
                "detail": f"Step {step.get('step_id', '?')} issued {len(tool_calls)} tool calls "
                          f"(max={MAX_TOOL_CALLS_PER_STEP}).",
                "step_id": step.get("step_id"),
            })

    if not anomalies:
        return None

    # Build evidence from the envelope records + anomaly descriptions
    evidence: list[dict[str, Any]] = []

    # Use the first envelope as the primary trace reference
    if envelopes:
        first = envelopes[0]
        evidence.append({
            "source_type": "trace",
            "source_ref": run_id,
            "observed_at": first["ts"],
            "summary": (
                f"Agent run {run_id} ({agent_name}) produced {len(steps)} steps; "
                f"{len(anomalies)} anomaly/anomalies detected."
            ),
        })

    for anomaly in anomalies[:3]:  # cap at 3 evidence items
        ts = started_at
        # Try to find the anomalous step's timestamp
        if anomaly.get("step_id"):
            for step in steps:
                if step.get("step_id") == anomaly["step_id"]:
                    ts = step.get("ts", started_at)
                    break
        evidence.append({
            "source_type": "trace",
            "source_ref": anomaly.get("step_id") or run_id,
            "observed_at": ts,
            "summary": anomaly["detail"],
        })

    if not evidence:
        # Fallback — must have at least one evidence item
        evidence.append({
            "source_type": "trace",
            "source_ref": run_id,
            "observed_at": started_at,
            "summary": f"Agent-drift anomalies detected in run {run_id}: "
                       f"{'; '.join(a['detail'] for a in anomalies[:2])}",
        })

    finding: dict[str, Any] = {
        "finding_id": finding_id or str(uuid.uuid4()),
        "title": f"Agent drift detected in run {run_id} ({agent_name})",
        "category": "aiops",
        "severity": "p2",
        "confidence": min(0.5 + 0.1 * len(anomalies), 0.90),
        "status": "open",
        "services": [agent_name],
        "first_seen": started_at,
        "last_seen": (steps[-1].get("ts") if steps else started_at) or started_at,
        "owner": f"team-{agent_name.split('-')[0].lower()}",
        "hypothesis": (
            f"Agent {agent_name} (run {run_id}) exhibited {len(anomalies)} anomalous "
            "behaviour pattern(s) suggesting drift from expected operating procedure."
        ),
        "suggested_fix": (
            "Review the agent run trace, inspect flagged steps, and verify the agent "
            "is operating within its defined autonomy level and allowed_paths."
        ),
        "blast_radius": "service",
        "sla_impact": False,
        "evidence": evidence,
    }

    return finding
