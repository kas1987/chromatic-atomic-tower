"""
Tests for LOGHOUSE drift detector (BEAD-05).

Covers each drift classification: intentional, accidental, blocked, unknown.
Covers the forbidden-edge finding.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.common import ROOT, validate_with_schema
from scripts.loghouse.drift import (
    load_architecture_rules,
    classify_edge,
    detect_drift,
)

FIXTURES = ROOT / "tests" / "fixtures" / "loghouse"
RULES_PATH = ROOT / "reference" / "loghouse" / "architecture_rules.yaml"
DRIFT_SCHEMA = ROOT / "schemas" / "drift_report.schema.json"
FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"

GOLDEN_REPORT_ID = "r1111111-1111-1111-1111-111111111111"
GOLDEN_FINDING_ID = "df111111-1111-1111-1111-111111111111"


def _sample_rules():
    return load_architecture_rules(RULES_PATH)


def test_load_architecture_rules():
    rules = _sample_rules()
    assert len(rules) >= 2
    for rule in rules:
        assert "rule_id" in rule
        assert "decision" in rule


def test_classify_intentional():
    rules = _sample_rules()
    edge = {
        "edge_id": "77777777-7777-7777-7777-777777777777",
        "source": "frontend",
        "target": "payments-api",
        "edge_type": "runtime",
        "observed_at": "2026-06-17T12:00:00Z",
        "confidence": 0.95,
        "allowed": True,
    }
    classification, rule_id = classify_edge(edge, rules)
    assert classification == "intentional"
    assert rule_id == "RULE-001"


def test_classify_blocked():
    rules = _sample_rules()
    edge = {
        "edge_id": "88888888-8888-8888-8888-888888888888",
        "source": "frontend",
        "target": "database",
        "edge_type": "runtime",
        "observed_at": "2026-06-17T12:00:00Z",
        "confidence": 0.9,
        "allowed": False,
    }
    classification, rule_id = classify_edge(edge, rules)
    assert classification == "blocked"
    assert rule_id == "RULE-002"


def test_classify_accidental():
    rules = _sample_rules()
    # Edge with allowed=False but no matching rule
    edge = {
        "edge_id": "aaaaeeee-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "source": "notification-svc",
        "target": "payments-api",
        "edge_type": "runtime",
        "observed_at": "2026-06-17T12:00:00Z",
        "confidence": 0.7,
        "allowed": False,
    }
    classification, rule_id = classify_edge(edge, rules)
    assert classification == "accidental"
    assert rule_id is None


def test_classify_unknown():
    rules = _sample_rules()
    # Edge with no matching rule and allowed=True
    edge = {
        "edge_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "source": "brand-new-service",
        "target": "unknown-target",
        "edge_type": "runtime",
        "observed_at": "2026-06-17T12:00:00Z",
        "confidence": 0.6,
        "allowed": True,
    }
    classification, rule_id = classify_edge(edge, rules)
    assert classification == "unknown"
    assert rule_id is None


def test_detect_drift_produces_valid_report():
    edges = json.loads((FIXTURES / "dependency_edges.json").read_text())
    rules = _sample_rules()

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        report, findings = detect_drift(
            edges,
            rules,
            out,
            report_id=GOLDEN_REPORT_ID,
            generated_at="2026-06-17T13:00:00Z",
        )

    errors = validate_with_schema(report, DRIFT_SCHEMA)
    assert errors == [], f"Drift report schema errors: {errors}"
    assert report["report_id"] == GOLDEN_REPORT_ID
    assert report["summary"]["total"] == len(edges)


def test_detect_drift_all_classifications_present():
    """The fixture has intentional, blocked, and unknown edges."""
    edges = json.loads((FIXTURES / "dependency_edges.json").read_text())
    rules = _sample_rules()

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        report, _ = detect_drift(
            edges,
            rules,
            out,
            generated_at="2026-06-17T13:00:00Z",
        )

    classifications = {e["classification"] for e in report["edges"]}
    assert "intentional" in classifications
    assert "blocked" in classifications
    # The fixture has a brand-new-service → unknown-target edge with allowed=True
    assert "unknown" in classifications


def test_blocked_edge_produces_finding():
    edges = json.loads((FIXTURES / "dependency_edges.json").read_text())
    rules = _sample_rules()

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        report, findings = detect_drift(
            edges,
            rules,
            out,
            generated_at="2026-06-17T13:00:00Z",
            finding_ids=[GOLDEN_FINDING_ID],
        )

    blocked_count = report["summary"]["blocked"]
    assert blocked_count >= 1
    assert len(findings) >= 1

    for finding in findings:
        errors = validate_with_schema(finding, FINDING_SCHEMA)
        assert errors == [], f"Blocked-edge finding schema errors: {errors}"
        assert len(finding["evidence"]) >= 1


def test_blocked_edge_finding_has_evidence():
    edges = json.loads((FIXTURES / "dependency_edges.json").read_text())
    rules = _sample_rules()

    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)
        _, findings = detect_drift(
            edges,
            rules,
            out,
            generated_at="2026-06-17T13:00:00Z",
        )

    assert findings
    for finding in findings:
        assert finding["evidence"], "Blocked-edge finding must have evidence"
