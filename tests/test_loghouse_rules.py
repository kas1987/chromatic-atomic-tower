"""
Tests for LOGHOUSE rules engine, findings engine, and dispatch writer (BEAD-04).

Goldens use hardcoded UUIDs so they are deterministic across runs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.common import ROOT, validate_with_schema
from scripts.loghouse.normalize import normalize_batch
from scripts.loghouse.correlate import correlate
from scripts.loghouse.rules import evaluate_windows, rule_forbidden_dependency_edge
from scripts.loghouse.findings import emit_findings, build_finding
from scripts.loghouse.dispatch import emit_dispatch, build_dispatch_item

FIXTURES = ROOT / "tests" / "fixtures" / "loghouse"
FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"
DISPATCH_SCHEMA = ROOT / "schemas" / "dispatch_queue_item.schema.json"

GOLDEN_FINDING_ID = "f1111111-1111-1111-1111-111111111111"
GOLDEN_DISPATCH_ID = "d1111111-1111-1111-1111-111111111111"


def _load_fixture_windows():
    raw = json.loads((FIXTURES / "raw_signals.json").read_text())
    envelopes, deploy_events, _ = normalize_batch(raw)
    return correlate(envelopes, deploy_events)


def test_error_spike_rule_fires_from_fixture():
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)
    spike_findings = [f for f in raw_findings if f["rule_id"] == "error-spike-after-deploy"]
    assert len(spike_findings) >= 1, "Expected at least one error-spike-after-deploy finding"


def test_error_spike_rule_has_evidence():
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)
    spike_findings = [f for f in raw_findings if f["rule_id"] == "error-spike-after-deploy"]
    assert len(spike_findings) >= 1
    finding = spike_findings[0]
    assert len(finding["evidence"]) >= 1
    ev = finding["evidence"][0]
    assert ev["source_type"] in ("deploy", "log", "metric", "trace", "dependency", "git", "catalog")
    assert ev["source_ref"]
    assert ev["observed_at"]
    assert ev["summary"]


def test_exception_explosion_rule_fires_from_fixture():
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)
    explosion_findings = [f for f in raw_findings if f["rule_id"] == "exception-explosion"]
    assert len(explosion_findings) >= 1, "Expected at least one exception-explosion finding"


def test_forbidden_edge_rule_fires():
    edges = json.loads((FIXTURES / "dependency_edges.json").read_text())
    findings = rule_forbidden_dependency_edge(edges)
    assert len(findings) >= 1
    for f in findings:
        assert len(f["evidence"]) >= 1


def test_golden_finding_validates():
    """Stable golden: normalize → correlate → rule → build_finding → validate schema."""
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)
    spike_raws = [f for f in raw_findings if f["rule_id"] == "error-spike-after-deploy"]
    assert spike_raws

    finding = build_finding(spike_raws[0], finding_id=GOLDEN_FINDING_ID)
    assert finding["finding_id"] == GOLDEN_FINDING_ID
    errors = validate_with_schema(finding, FINDING_SCHEMA)
    assert errors == [], f"Golden finding schema errors: {errors}"


def test_golden_dispatch_item_validates():
    """Stable golden: finding → dispatch item → validate schema."""
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)
    spike_raws = [f for f in raw_findings if f["rule_id"] == "error-spike-after-deploy"]
    finding = build_finding(spike_raws[0], finding_id=GOLDEN_FINDING_ID)

    item = build_dispatch_item(
        finding,
        dispatch_id=GOLDEN_DISPATCH_ID,
        created_at="2026-06-17T13:00:00Z",
    )
    assert item["id"] == GOLDEN_DISPATCH_ID
    assert item["finding_id"] == GOLDEN_FINDING_ID
    errors = validate_with_schema(item, DISPATCH_SCHEMA)
    assert errors == [], f"Golden dispatch item schema errors: {errors}"


def test_emit_findings_writes_json_and_md():
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        validated = emit_findings(raw_findings, out)
        assert len(validated) >= 1
        assert (out / "findings.json").exists()
        assert (out / "findings.md").exists()


def test_emit_dispatch_writes_json():
    windows = _load_fixture_windows()
    raw_findings = evaluate_windows(windows)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        validated = emit_findings(raw_findings, out)
        items = emit_dispatch(validated, out)
        assert len(items) >= 1
        assert (out / "dispatch_queue.json").exists()


# ── Additional rules coverage ─────────────────────────────────────────────────

from scripts.loghouse.correlate import CorrelationWindow
from scripts.loghouse.rules import (
    ERROR_SPIKE_THRESHOLD,
    EXCEPTION_EXPLOSION_THRESHOLD,
    rule_error_spike_after_deploy,
    rule_exception_explosion,
    rule_bead_stuck_in_state,
    rule_go_block_frequency,
    rule_closeout_rejection_spike,
    rule_confidence_below_threshold,
)
from datetime import datetime, timedelta, timezone


def _make_window(service="payments-api", deploy_id="deploy-001", commit_sha="abc1234", envelopes=None, deploy_events=None):
    """Build a minimal CorrelationWindow for unit tests."""
    w = CorrelationWindow(
        service=service,
        env="prod",
        commit_sha=commit_sha,
        deploy_id=deploy_id,
    )
    w.envelopes = envelopes or []
    w.deploy_events = deploy_events or []
    return w


def _make_error_envelope(event_id="evt-001", ts="2026-06-17T12:05:00Z", severity="error", message="oops"):
    return {
        "event_id": event_id,
        "ts": ts,
        "signal_type": "log",
        "service": "payments-api",
        "env": "prod",
        "severity": severity,
        "message": message,
        "commit_sha": "abc1234",
        "deploy_id": "deploy-001",
        "attrs": {},
    }


def _make_deploy_event(deploy_id="deploy-001", completed_at="2026-06-17T12:01:00Z"):
    return {
        "deploy_id": deploy_id,
        "service": "payments-api",
        "commit_sha": "abc1234",
        "actor": "ci",
        "started_at": "2026-06-17T11:59:00Z",
        "completed_at": completed_at,
        "status": "succeeded",
    }


# ── Error-spike rule unit tests ───────────────────────────────────────────────


def test_error_spike_rule_requires_deploy_event():
    """No deploy → no finding regardless of error count."""
    envelopes = [_make_error_envelope(event_id=f"e{i}") for i in range(5)]
    window = _make_window(envelopes=envelopes, deploy_events=[])
    result = rule_error_spike_after_deploy(window)
    assert result is None


def test_error_spike_rule_requires_threshold_errors():
    """Deploy present but errors below threshold → no finding."""
    envelopes = [_make_error_envelope(event_id=f"e{i}") for i in range(ERROR_SPIKE_THRESHOLD - 1)]
    window = _make_window(envelopes=envelopes, deploy_events=[_make_deploy_event()])
    result = rule_error_spike_after_deploy(window)
    assert result is None


def test_error_spike_rule_fires_at_exact_threshold():
    """Exactly ERROR_SPIKE_THRESHOLD errors → fires."""
    envelopes = [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:0{i+5}:00Z")
        for i in range(ERROR_SPIKE_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes, deploy_events=[_make_deploy_event()])
    result = rule_error_spike_after_deploy(window)
    assert result is not None
    assert result["rule_id"] == "error-spike-after-deploy"


def test_error_spike_rule_severity_is_p1():
    envelopes = [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:0{i+5}:00Z")
        for i in range(ERROR_SPIKE_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes, deploy_events=[_make_deploy_event()])
    result = rule_error_spike_after_deploy(window)
    assert result["severity"] == "p1"


def test_error_spike_rule_has_two_evidence_items():
    envelopes = [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:0{i+5}:00Z")
        for i in range(ERROR_SPIKE_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes, deploy_events=[_make_deploy_event()])
    result = rule_error_spike_after_deploy(window)
    # First evidence is deploy, second is first error log
    assert len(result["evidence"]) == 2
    assert result["evidence"][0]["source_type"] == "deploy"
    assert result["evidence"][1]["source_type"] == "log"


def test_error_spike_rule_confidence_increases_with_more_errors():
    make_envs = lambda n: [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:{i+10}:00Z")
        for i in range(n)
    ]
    w3 = _make_window(envelopes=make_envs(3), deploy_events=[_make_deploy_event()])
    w8 = _make_window(envelopes=make_envs(8), deploy_events=[_make_deploy_event()])
    r3 = rule_error_spike_after_deploy(w3)
    r8 = rule_error_spike_after_deploy(w8)
    assert r3["confidence"] < r8["confidence"]


def test_error_spike_rule_ignores_non_error_severity():
    """Only error/fatal count, not info/warning."""
    envelopes = [
        _make_error_envelope(event_id="e1", severity="info"),
        _make_error_envelope(event_id="e2", severity="warning"),
        _make_error_envelope(event_id="e3", severity="info"),
    ]
    window = _make_window(envelopes=envelopes, deploy_events=[_make_deploy_event()])
    result = rule_error_spike_after_deploy(window)
    assert result is None


# ── Exception-explosion rule unit tests ──────────────────────────────────────


def test_exception_explosion_requires_threshold():
    """Below threshold → no finding."""
    envelopes = [_make_error_envelope(event_id=f"e{i}") for i in range(EXCEPTION_EXPLOSION_THRESHOLD - 1)]
    window = _make_window(envelopes=envelopes)
    result = rule_exception_explosion(window)
    assert result is None


def test_exception_explosion_fires_at_threshold():
    envelopes = [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:0{i+1}:00Z")
        for i in range(EXCEPTION_EXPLOSION_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes)
    result = rule_exception_explosion(window)
    assert result is not None
    assert result["rule_id"] == "exception-explosion"


def test_exception_explosion_counts_traceback_messages():
    """Messages containing 'traceback' count toward the threshold."""
    envelopes = [
        {**_make_error_envelope(event_id=f"e{i}", severity="info"), "message": f"traceback {i}"}
        for i in range(EXCEPTION_EXPLOSION_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes)
    result = rule_exception_explosion(window)
    assert result is not None


def test_exception_explosion_severity_is_p2():
    envelopes = [
        _make_error_envelope(event_id=f"e{i}", ts=f"2026-06-17T12:0{i+5}:00Z")
        for i in range(EXCEPTION_EXPLOSION_THRESHOLD)
    ]
    window = _make_window(envelopes=envelopes)
    result = rule_exception_explosion(window)
    assert result["severity"] == "p2"


# ── Forbidden-edge rule unit tests ────────────────────────────────────────────


def test_forbidden_edge_rule_no_findings_on_allowed_edges():
    edges = [
        {
            "edge_id": "e1",
            "source": "frontend",
            "target": "payments-api",
            "edge_type": "runtime",
            "allowed": True,
            "observed_at": "2026-06-17T12:00:00Z",
            "confidence": 0.9,
        }
    ]
    findings = rule_forbidden_dependency_edge(edges)
    assert findings == []


def test_forbidden_edge_rule_fires_on_disallowed_edge():
    edges = [
        {
            "edge_id": "edge-forbidden-001",
            "source": "frontend",
            "target": "database",
            "edge_type": "runtime",
            "allowed": False,
            "observed_at": "2026-06-17T12:00:00Z",
            "confidence": 0.85,
        }
    ]
    findings = rule_forbidden_dependency_edge(edges)
    assert len(findings) == 1
    f = findings[0]
    assert f["rule_id"] == "forbidden-dependency-edge"
    assert f["category"] == "drift"
    assert f["evidence"][0]["source_ref"] == "edge-forbidden-001"


def test_forbidden_edge_rule_skips_none_allowed():
    """allowed=None (missing/unset) should not produce a finding."""
    edges = [
        {
            "edge_id": "e2",
            "source": "svc-a",
            "target": "svc-b",
            "edge_type": "runtime",
            "observed_at": "2026-06-17T12:00:00Z",
            "confidence": 0.5,
            # allowed not set
        }
    ]
    findings = rule_forbidden_dependency_edge(edges)
    assert findings == []


def test_forbidden_edge_rule_empty_edge_list():
    findings = rule_forbidden_dependency_edge([])
    assert findings == []


# ── CAT governance rule unit tests ────────────────────────────────────────────


def _make_go_block_envelope(ts: str, drifts: list[str] | None = None) -> dict:
    return {
        "event_id": f"go-{ts}",
        "ts": ts,
        "signal_type": "go_decision",
        "service": "cat",
        "env": "prod",
        "severity": "info",
        "message": "GO blocked",
        "commit_sha": "abc",
        "deploy_id": "d-cat",
        "attrs": {"allowed": False, "drifts": drifts or ["alignment-drift"]},
    }


def test_go_block_frequency_fires_at_p1_threshold():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    envelopes = [
        _make_go_block_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(3)  # exactly GO_BLOCK_P1_THRESHOLD
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    result = rule_go_block_frequency(window)
    assert result is not None
    assert result["rule_id"] == "go-block-frequency"
    assert result["severity"] == "p1"


def test_go_block_frequency_fires_p0_at_five_blocks():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    envelopes = [
        _make_go_block_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(5)  # GO_BLOCK_P0_THRESHOLD
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    result = rule_go_block_frequency(window)
    assert result is not None
    assert result["severity"] == "p0"


def test_go_block_frequency_no_finding_below_threshold():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    envelopes = [
        _make_go_block_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(2)  # below P1 threshold
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    result = rule_go_block_frequency(window)
    assert result is None


def test_go_block_frequency_only_fires_on_cat_service():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    envelopes = [
        _make_go_block_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(5)
    ]
    # Non-CAT window should produce no finding
    window = _make_window(service="payments-api", envelopes=envelopes)
    result = rule_go_block_frequency(window)
    assert result is None


def _make_closeout_envelope(ts: str, allowed: bool, reason: str = "") -> dict:
    return {
        "event_id": f"co-{ts}-{'ok' if allowed else 'rej'}",
        "ts": ts,
        "signal_type": "closeout",
        "service": "cat",
        "env": "prod",
        "severity": "info",
        "message": "closeout",
        "commit_sha": "abc",
        "deploy_id": "d-cat",
        "attrs": {"allowed": allowed, "reason": reason},
    }


def test_closeout_rejection_spike_fires_at_p2():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    # 2 rejected out of 3 = 66% ≥ 50% → P2
    envelopes = [
        _make_closeout_envelope((base + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"), allowed=False, reason="missing-evidence"),
        _make_closeout_envelope((base + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"), allowed=False, reason="missing-evidence"),
        _make_closeout_envelope((base + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"), allowed=True),
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    result = rule_closeout_rejection_spike(window)
    assert result is not None
    assert result["rule_id"] == "closeout-rejection-spike"
    assert result["severity"] == "p2"


def test_closeout_rejection_spike_no_finding_below_threshold():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    # 1 rejected out of 4 = 25% < 50%
    envelopes = [
        _make_closeout_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"), allowed=(i != 0))
        for i in range(4)
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    result = rule_closeout_rejection_spike(window)
    assert result is None


def test_closeout_rejection_spike_only_fires_on_cat_service():
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    envelopes = [
        _make_closeout_envelope((base + timedelta(minutes=i * 10)).strftime("%Y-%m-%dT%H:%M:%SZ"), allowed=False)
        for i in range(4)
    ]
    window = _make_window(service="other-svc", envelopes=envelopes)
    result = rule_closeout_rejection_spike(window)
    assert result is None


def test_confidence_below_threshold_fires_for_low_score():
    envelopes = [
        {
            "event_id": "ar-001",
            "ts": "2026-06-17T12:00:00Z",
            "signal_type": "agent_run",
            "service": "cat",
            "env": "prod",
            "severity": "info",
            "message": "agent run complete",
            "commit_sha": "abc",
            "deploy_id": "d-cat",
            "attrs": {
                "confidence_score": 55,
                "task_id": "BEAD-09",
                "model": "claude-sonnet-4-6",
                "result": "analysis complete",
            },
        }
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    findings = rule_confidence_below_threshold(window)
    assert len(findings) == 1
    f = findings[0]
    assert f["rule_id"] == "confidence-below-threshold"
    assert f["severity"] == "p2"
    assert "BEAD-09" in f["title"]


def test_confidence_below_threshold_no_finding_at_minimum():
    envelopes = [
        {
            "event_id": "ar-002",
            "ts": "2026-06-17T12:01:00Z",
            "signal_type": "agent_run",
            "service": "cat",
            "env": "prod",
            "severity": "info",
            "message": "agent run complete",
            "commit_sha": "abc",
            "deploy_id": "d-cat",
            "attrs": {
                "confidence_score": 70,  # exactly at minimum — should NOT fire
                "task_id": "BEAD-10",
                "model": "claude-sonnet-4-6",
                "result": "done",
            },
        }
    ]
    window = _make_window(service="cat", envelopes=envelopes)
    findings = rule_confidence_below_threshold(window)
    assert findings == []


def test_confidence_below_threshold_only_fires_on_cat_service():
    envelopes = [
        {
            "event_id": "ar-003",
            "ts": "2026-06-17T12:02:00Z",
            "signal_type": "agent_run",
            "service": "payments-api",
            "env": "prod",
            "severity": "info",
            "message": "agent run",
            "commit_sha": "abc",
            "deploy_id": "d-001",
            "attrs": {"confidence_score": 40, "task_id": "T-01", "model": "x", "result": "y"},
        }
    ]
    window = _make_window(service="payments-api", envelopes=envelopes)
    findings = rule_confidence_below_threshold(window)
    assert findings == []


# ── evaluate_windows: clean state and empty inputs ────────────────────────────


def test_evaluate_windows_empty_windows_and_edges():
    findings = evaluate_windows([])
    assert findings == []


def test_evaluate_windows_empty_with_empty_edges():
    findings = evaluate_windows([], dependency_edges=[])
    assert findings == []


def test_evaluate_windows_no_findings_on_clean_window():
    """A window with only info-severity logs produces no findings."""
    envelopes = [
        {
            "event_id": f"e{i}",
            "ts": f"2026-06-17T12:0{i}:00Z",
            "signal_type": "log",
            "service": "auth-svc",
            "env": "prod",
            "severity": "info",
            "message": "all good",
            "commit_sha": "sha123",
            "deploy_id": "d-clean",
            "attrs": {},
        }
        for i in range(5)
    ]
    window = _make_window(service="auth-svc", deploy_id="d-clean", commit_sha="sha123", envelopes=envelopes)
    findings = evaluate_windows([window])
    assert findings == []


def test_evaluate_windows_no_findings_on_empty_signals():
    """A window with no envelopes at all should not fire any rules."""
    window = _make_window(service="svc-x")
    findings = evaluate_windows([window])
    assert findings == []


def test_evaluate_windows_forbidden_edges_processed_separately():
    """evaluate_windows accepts dependency_edges and routes them to the correct rule."""
    edges = [
        {
            "edge_id": "edge-001",
            "source": "frontend",
            "target": "database",
            "edge_type": "runtime",
            "allowed": False,
            "observed_at": "2026-06-17T12:00:00Z",
            "confidence": 0.9,
        }
    ]
    findings = evaluate_windows([], dependency_edges=edges)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "forbidden-dependency-edge"


def test_evaluate_windows_cat_rules_skipped_for_non_cat_service():
    """Go-block and closeout rules must not fire on non-CAT service windows."""
    base = datetime(2026, 6, 17, 10, 0, 0, tzinfo=timezone.utc)
    go_envelopes = [
        _make_go_block_envelope((base + timedelta(minutes=i * 5)).strftime("%Y-%m-%dT%H:%M:%SZ"))
        for i in range(5)
    ]
    # Assign to a non-cat service window
    for ev in go_envelopes:
        ev["service"] = "orders-svc"
    window = _make_window(service="orders-svc", envelopes=go_envelopes)
    findings = evaluate_windows([window])
    # No CAT governance findings, and no service-telemetry findings (go_decision is not error/exception)
    governance_findings = [f for f in findings if f.get("category") == "governance"]
    assert governance_findings == []
