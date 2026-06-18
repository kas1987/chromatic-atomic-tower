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
