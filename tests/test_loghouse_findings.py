"""
Tests for LOGHOUSE Findings Engine (scripts/loghouse/findings.py).

Covers: build_finding construction, ID generation, evidence linking,
field propagation, validation, error cases, emit_findings I/O.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from scripts.common import ROOT, validate_with_schema
from scripts.loghouse.findings import (
    STATIC_FINDING_ID,
    build_finding,
    emit_findings,
    _render_markdown,
)

FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"

GOLDEN_FINDING_ID = "f3333333-3333-3333-3333-333333333333"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_raw(
    *,
    title: str = "Error spike after deploy in payments-api",
    category: str = "reliability",
    severity: str = "p1",
    confidence: float = 0.80,
    services: list[str] | None = None,
    owner: str = "team-payments",
    evidence: list[dict] | None = None,
) -> dict:
    if services is None:
        services = ["payments-api"]
    if evidence is None:
        evidence = [
            {
                "source_type": "deploy",
                "source_ref": "deploy-20260617-1200",
                "observed_at": "2026-06-17T12:05:00Z",
                "summary": "Deploy completed; errors observed.",
            }
        ]
    return {
        "title": title,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "services": services,
        "first_seen": "2026-06-17T12:05:00Z",
        "last_seen": "2026-06-17T12:10:00Z",
        "owner": owner,
        "hypothesis": "Deploy introduced regression.",
        "suggested_fix": "Roll back the deploy.",
        "blast_radius": "service",
        "sla_impact": True,
        "evidence": evidence,
    }


# ── build_finding: ID generation ──────────────────────────────────────────────


def test_build_finding_uses_provided_id():
    raw = _make_raw()
    finding = build_finding(raw, finding_id=GOLDEN_FINDING_ID)
    assert finding["finding_id"] == GOLDEN_FINDING_ID


def test_build_finding_generates_uuid_when_no_id():
    raw = _make_raw()
    finding = build_finding(raw)
    parsed = uuid.UUID(finding["finding_id"])
    assert str(parsed) == finding["finding_id"]


def test_build_finding_ids_are_unique_across_calls():
    raw = _make_raw()
    id1 = build_finding(raw)["finding_id"]
    id2 = build_finding(raw)["finding_id"]
    assert id1 != id2


def test_static_finding_id_constant_is_valid_uuid():
    parsed = uuid.UUID(STATIC_FINDING_ID)
    assert str(parsed) == STATIC_FINDING_ID


# ── build_finding: field propagation ─────────────────────────────────────────


def test_build_finding_status_is_open():
    finding = build_finding(_make_raw())
    assert finding["status"] == "open"


def test_build_finding_title_propagated():
    finding = build_finding(_make_raw(title="My custom title"))
    assert finding["title"] == "My custom title"


def test_build_finding_category_propagated():
    finding = build_finding(_make_raw(category="governance"))
    assert finding["category"] == "governance"


def test_build_finding_severity_propagated():
    for sev in ("p0", "p1", "p2", "p3"):
        finding = build_finding(_make_raw(severity=sev))
        assert finding["severity"] == sev


def test_build_finding_confidence_propagated():
    finding = build_finding(_make_raw(confidence=0.73))
    assert abs(finding["confidence"] - 0.73) < 1e-9


def test_build_finding_services_propagated():
    finding = build_finding(_make_raw(services=["svc-a", "svc-b"]))
    assert finding["services"] == ["svc-a", "svc-b"]


def test_build_finding_owner_propagated():
    finding = build_finding(_make_raw(owner="team-platform"))
    assert finding["owner"] == "team-platform"


def test_build_finding_evidence_linked():
    evidence = [
        {
            "source_type": "log",
            "source_ref": "evt-abc-001",
            "observed_at": "2026-06-17T12:06:00Z",
            "summary": "Exception trace captured.",
        }
    ]
    finding = build_finding(_make_raw(evidence=evidence))
    assert len(finding["evidence"]) == 1
    assert finding["evidence"][0]["source_ref"] == "evt-abc-001"


def test_build_finding_multiple_evidence_items():
    evidence = [
        {
            "source_type": "deploy",
            "source_ref": "deploy-001",
            "observed_at": "2026-06-17T12:00:00Z",
            "summary": "Deploy event.",
        },
        {
            "source_type": "log",
            "source_ref": "evt-001",
            "observed_at": "2026-06-17T12:05:00Z",
            "summary": "First error log.",
        },
    ]
    finding = build_finding(_make_raw(evidence=evidence))
    assert len(finding["evidence"]) == 2


# ── build_finding: error cases ────────────────────────────────────────────────


def test_build_finding_raises_on_empty_evidence():
    raw = _make_raw(evidence=[])
    with pytest.raises(ValueError, match="no evidence"):
        build_finding(raw)


def test_build_finding_raises_on_missing_evidence_key():
    raw = _make_raw()
    del raw["evidence"]
    with pytest.raises((ValueError, KeyError)):
        build_finding(raw)


# ── schema validation ─────────────────────────────────────────────────────────


def test_build_finding_passes_schema_validation():
    finding = build_finding(_make_raw(), finding_id=GOLDEN_FINDING_ID)
    errors = validate_with_schema(finding, FINDING_SCHEMA)
    assert errors == [], f"Schema errors: {errors}"


def test_build_finding_governance_category_passes_schema():
    raw = _make_raw(category="governance")
    raw["blast_radius"] = "bead"
    raw["sla_impact"] = False
    finding = build_finding(raw, finding_id=GOLDEN_FINDING_ID)
    errors = validate_with_schema(finding, FINDING_SCHEMA)
    assert errors == [], f"Schema errors: {errors}"


# ── emit_findings ─────────────────────────────────────────────────────────────


def test_emit_findings_creates_findings_json(tmp_path):
    raws = [_make_raw()]
    emit_findings(raws, tmp_path)
    assert (tmp_path / "findings.json").exists()


def test_emit_findings_creates_findings_md(tmp_path):
    raws = [_make_raw()]
    emit_findings(raws, tmp_path)
    assert (tmp_path / "findings.md").exists()


def test_emit_findings_returns_validated_list(tmp_path):
    raws = [_make_raw()]
    validated = emit_findings(raws, tmp_path)
    assert len(validated) == 1
    assert validated[0]["status"] == "open"


def test_emit_findings_stable_ids(tmp_path):
    raws = [_make_raw()]
    validated = emit_findings(raws, tmp_path, finding_ids=[GOLDEN_FINDING_ID])
    assert validated[0]["finding_id"] == GOLDEN_FINDING_ID


def test_emit_findings_json_is_parseable_list(tmp_path):
    raws = [_make_raw()]
    emit_findings(raws, tmp_path)
    loaded = json.loads((tmp_path / "findings.json").read_text())
    assert isinstance(loaded, list)
    assert len(loaded) == 1


def test_emit_findings_skips_no_evidence_raw(tmp_path):
    valid = _make_raw()
    invalid = _make_raw(evidence=[])
    # invalid will raise ValueError → should be skipped, not crash
    validated = emit_findings([valid, invalid], tmp_path)
    assert len(validated) == 1


def test_emit_findings_empty_input_writes_empty_list(tmp_path):
    validated = emit_findings([], tmp_path)
    assert validated == []
    loaded = json.loads((tmp_path / "findings.json").read_text())
    assert loaded == []


def test_emit_findings_creates_output_dir(tmp_path):
    out = tmp_path / "subdir"
    assert not out.exists()
    emit_findings([_make_raw()], out)
    assert out.exists()


def test_emit_findings_multiple_all_validated(tmp_path):
    raws = [
        _make_raw(
            title="Error spike after deploy in svc-a",
            services=["svc-a"],
        ),
        _make_raw(
            title="Exception explosion in svc-b",
            category="reliability",
            severity="p2",
            services=["svc-b"],
        ),
    ]
    validated = emit_findings(raws, tmp_path)
    assert len(validated) == 2
    for f in validated:
        errors = validate_with_schema(f, FINDING_SCHEMA)
        assert errors == [], f"Schema errors: {errors}"


# ── _render_markdown ──────────────────────────────────────────────────────────


def test_render_markdown_empty_findings():
    md = _render_markdown([])
    assert "No findings detected" in md


def test_render_markdown_includes_title():
    finding = build_finding(_make_raw(title="Test finding title"), finding_id=GOLDEN_FINDING_ID)
    md = _render_markdown([finding])
    assert "Test finding title" in md


def test_render_markdown_includes_finding_id():
    finding = build_finding(_make_raw(), finding_id=GOLDEN_FINDING_ID)
    md = _render_markdown([finding])
    assert GOLDEN_FINDING_ID in md


def test_render_markdown_includes_severity():
    finding = build_finding(_make_raw(severity="p0"), finding_id=GOLDEN_FINDING_ID)
    md = _render_markdown([finding])
    assert "p0" in md
