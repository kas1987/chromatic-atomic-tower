"""Unit tests for scripts/loghouse/agent_obs.py.

Validates trace -> telemetry-envelope mapping and the agent-drift finding
detector against the live schemas. Generated envelopes/findings must validate
against telemetry_envelope.schema.json and finding.schema.json respectively.
"""
from __future__ import annotations

from scripts.common import ROOT, validate_with_schema
from scripts.loghouse import agent_obs as ao

ENVELOPE_SCHEMA = ROOT / "schemas" / "telemetry_envelope.schema.json"
FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"


def _trace(steps):
    return {
        "run_id": "run-abc123",
        "agent": "BUILDER",
        "commit_sha": "abc1234",
        "started_at": "2026-06-17T12:00:00Z",
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# trace_to_envelopes
# ---------------------------------------------------------------------------

def test_trace_to_envelopes_emits_validated_event():
    trace = _trace([
        {
            "step_id": "step-001",
            "ts": "2026-06-17T12:00:01Z",
            "tool": "Read",
            "input": {"file_path": "/some/file.py"},
            "output_summary": "read 100 lines",
            "duration_ms": 120,
        },
    ])
    envelopes = ao.trace_to_envelopes(trace)
    assert len(envelopes) == 1
    rec = envelopes[0]
    assert rec["signal_type"] == "event"
    assert rec["service"] == "BUILDER"
    assert rec["commit_sha"] == "abc1234"
    assert rec["attrs"]["tool"] == "Read"
    assert "input_summary" in rec["attrs"]
    assert validate_with_schema(rec, ENVELOPE_SCHEMA) == []


def test_trace_to_envelopes_trace_signal_when_trace_id_present():
    trace = _trace([
        {"step_id": "s1", "ts": "2026-06-17T12:00:01Z", "tool": "Bash",
         "trace_id": "trace-xyz", "output_summary": "ran"},
    ])
    envelopes = ao.trace_to_envelopes(trace)
    assert envelopes[0]["signal_type"] == "trace"
    assert envelopes[0]["trace_id"] == "trace-xyz"


def test_trace_to_envelopes_overrides_apply():
    trace = _trace([
        {"step_id": "s1", "ts": "2026-06-17T12:00:01Z", "tool": "Read",
         "output_summary": "x"},
    ])
    envelopes = ao.trace_to_envelopes(
        trace, service="OVERRIDE", env="prod", commit_sha="deadbee", deploy_id="dep-1",
    )
    rec = envelopes[0]
    assert rec["service"] == "OVERRIDE"
    assert rec["env"] == "prod"
    assert rec["commit_sha"] == "deadbee"
    assert rec["deploy_id"] == "dep-1"


def test_trace_to_envelopes_empty_steps():
    assert ao.trace_to_envelopes(_trace([])) == []


# ---------------------------------------------------------------------------
# detect_agent_drift
# ---------------------------------------------------------------------------

def test_detect_agent_drift_none_for_clean_run():
    trace = _trace([
        {"step_id": "s1", "ts": "2026-06-17T12:00:01Z", "tool": "Read",
         "output_summary": "ok"},
    ])
    envelopes = ao.trace_to_envelopes(trace)
    assert ao.detect_agent_drift(trace, envelopes) is None


def test_detect_agent_drift_step_overflow():
    steps = [
        {"step_id": f"s{i}", "ts": "2026-06-17T12:00:01Z", "tool": "Read",
         "output_summary": "x"}
        for i in range(ao.MAX_STEPS + 1)
    ]
    trace = _trace(steps)
    envelopes = ao.trace_to_envelopes(trace)
    finding = ao.detect_agent_drift(trace, envelopes)
    assert finding is not None
    assert finding["category"] == "aiops"
    assert finding["status"] == "open"
    assert validate_with_schema(finding, FINDING_SCHEMA) == []


def test_detect_agent_drift_forbidden_pattern():
    trace = _trace([
        {"step_id": "s1", "ts": "2026-06-17T12:00:01Z", "tool": "Bash",
         "input": {"cmd": "rm -rf /tmp/x"}, "output_summary": "ran"},
    ])
    envelopes = ao.trace_to_envelopes(trace)
    finding = ao.detect_agent_drift(trace, envelopes)
    assert finding is not None
    assert any("forbidden" in e["summary"].lower() or "rm -rf" in e["summary"]
               for e in finding["evidence"])
    assert validate_with_schema(finding, FINDING_SCHEMA) == []


def test_detect_agent_drift_tool_call_burst():
    trace = _trace([
        {"step_id": "s1", "ts": "2026-06-17T12:00:01Z", "tool": "Multi",
         "output_summary": "burst",
         "tool_calls": list(range(ao.MAX_TOOL_CALLS_PER_STEP + 1))},
    ])
    envelopes = ao.trace_to_envelopes(trace)
    finding = ao.detect_agent_drift(trace, envelopes)
    assert finding is not None
    assert validate_with_schema(finding, FINDING_SCHEMA) == []


def test_detect_agent_drift_confidence_capped():
    # Many anomalies should not push confidence above the 0.90 cap.
    steps = [
        {"step_id": f"s{i}", "ts": "2026-06-17T12:00:01Z", "tool": "Bash",
         "input": {"cmd": "drop table t"}, "output_summary": "x"}
        for i in range(10)
    ]
    trace = _trace(steps)
    envelopes = ao.trace_to_envelopes(trace)
    finding = ao.detect_agent_drift(trace, envelopes)
    assert finding["confidence"] <= 0.90
