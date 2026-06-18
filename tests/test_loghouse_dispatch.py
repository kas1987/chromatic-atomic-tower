"""
Tests for LOGHOUSE Dispatch Writer (scripts/loghouse/dispatch.py).

Covers: dispatch_queue_item construction, rule-to-agent routing,
template selection, evidence reference extraction, edge cases.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from scripts.common import ROOT, validate_with_schema
from scripts.loghouse.dispatch import (
    ACCEPTANCE_TEMPLATES,
    RULE_TO_AGENT,
    STATIC_DISPATCH_ID,
    STOP_TEMPLATES,
    _infer_rule_id,
    build_dispatch_item,
    emit_dispatch,
)

DISPATCH_SCHEMA = ROOT / "schemas" / "dispatch_queue_item.schema.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

GOLDEN_FINDING_ID = "f2222222-2222-2222-2222-222222222222"
GOLDEN_DISPATCH_ID = "d2222222-2222-2222-2222-222222222222"


def _make_finding(
    *,
    finding_id: str = GOLDEN_FINDING_ID,
    title: str = "Error spike after deploy in payments-api",
    category: str = "reliability",
    severity: str = "p1",
    owner: str = "team-payments",
    source_ref: str = "deploy-20260617-1200",
    source_type: str = "deploy",
) -> dict:
    return {
        "finding_id": finding_id,
        "title": title,
        "category": category,
        "severity": severity,
        "confidence": 0.85,
        "status": "open",
        "services": ["payments-api"],
        "first_seen": "2026-06-17T12:05:00Z",
        "last_seen": "2026-06-17T12:10:00Z",
        "owner": owner,
        "hypothesis": "A deploy caused an error spike.",
        "suggested_fix": "Roll back the deploy.",
        "blast_radius": "service",
        "sla_impact": True,
        "evidence": [
            {
                "source_type": source_type,
                "source_ref": source_ref,
                "observed_at": "2026-06-17T12:05:00Z",
                "summary": "First evidence item.",
            }
        ],
    }


# ── build_dispatch_item: structure ────────────────────────────────────────────


def test_build_dispatch_item_has_required_keys():
    finding = _make_finding()
    item = build_dispatch_item(finding, dispatch_id=GOLDEN_DISPATCH_ID)
    required = {
        "id", "finding_id", "owner", "agent_role", "evidence_ref",
        "acceptance_criteria", "stop_condition", "priority", "status",
    }
    assert required.issubset(item.keys())


def test_build_dispatch_item_id_is_provided_value():
    finding = _make_finding()
    item = build_dispatch_item(finding, dispatch_id=GOLDEN_DISPATCH_ID)
    assert item["id"] == GOLDEN_DISPATCH_ID


def test_build_dispatch_item_id_is_uuid_when_not_provided():
    finding = _make_finding()
    item = build_dispatch_item(finding)
    # Must be a valid UUID string
    parsed = uuid.UUID(item["id"])
    assert str(parsed) == item["id"]


def test_build_dispatch_item_finding_id_matches():
    finding = _make_finding(finding_id=GOLDEN_FINDING_ID)
    item = build_dispatch_item(finding, dispatch_id=GOLDEN_DISPATCH_ID)
    assert item["finding_id"] == GOLDEN_FINDING_ID


def test_build_dispatch_item_owner_propagated():
    finding = _make_finding(owner="team-frontend")
    item = build_dispatch_item(finding)
    assert item["owner"] == "team-frontend"


def test_build_dispatch_item_status_is_queued():
    finding = _make_finding()
    item = build_dispatch_item(finding)
    assert item["status"] == "queued"


def test_build_dispatch_item_priority_matches_severity():
    for sev in ("p0", "p1", "p2", "p3"):
        finding = _make_finding(severity=sev)
        item = build_dispatch_item(finding)
        assert item["priority"] == sev


def test_build_dispatch_item_evidence_ref_from_first_evidence():
    finding = _make_finding(source_ref="deploy-abc-001")
    item = build_dispatch_item(finding)
    assert item["evidence_ref"] == "deploy-abc-001"


def test_build_dispatch_item_created_at_included_when_provided():
    finding = _make_finding()
    item = build_dispatch_item(finding, created_at="2026-06-17T13:00:00Z")
    assert item["created_at"] == "2026-06-17T13:00:00Z"


def test_build_dispatch_item_no_created_at_when_none():
    finding = _make_finding()
    item = build_dispatch_item(finding)
    assert "created_at" not in item


def test_build_dispatch_item_passes_schema_validation():
    finding = _make_finding()
    item = build_dispatch_item(finding, dispatch_id=GOLDEN_DISPATCH_ID)
    errors = validate_with_schema(item, DISPATCH_SCHEMA)
    assert errors == [], f"Schema errors: {errors}"


# ── Rule-to-agent routing ─────────────────────────────────────────────────────


def test_routing_error_spike_goes_to_builder():
    finding = _make_finding(title="Error spike after deploy in payments-api")
    item = build_dispatch_item(finding)
    assert item["agent_role"] == "BUILDER"


def test_routing_forbidden_dependency_goes_to_auditor():
    finding = _make_finding(title="Forbidden dependency: frontend → database")
    item = build_dispatch_item(finding)
    assert item["agent_role"] == "AUDITOR"


def test_routing_exception_explosion_goes_to_builder():
    finding = _make_finding(title="Exception explosion in svc-a")
    item = build_dispatch_item(finding)
    assert item["agent_role"] == "BUILDER"


def test_routing_drift_title_goes_to_auditor():
    # Title contains "drift" but not "forbidden"/"dependency" → maps to forbidden-edge-drift → AUDITOR
    finding = _make_finding(title="Edge drift detected in svc-b")
    item = build_dispatch_item(finding)
    assert item["agent_role"] == "AUDITOR"


def test_routing_unknown_title_falls_back_to_reviewer():
    finding = _make_finding(title="Something completely unrelated")
    item = build_dispatch_item(finding)
    assert item["agent_role"] == "REVIEWER"


# ── Template selection ────────────────────────────────────────────────────────


def test_acceptance_criteria_p0_text():
    finding = _make_finding(severity="p0")
    item = build_dispatch_item(finding)
    assert item["acceptance_criteria"] == ACCEPTANCE_TEMPLATES["p0"]


def test_acceptance_criteria_p1_text():
    finding = _make_finding(severity="p1")
    item = build_dispatch_item(finding)
    assert item["acceptance_criteria"] == ACCEPTANCE_TEMPLATES["p1"]


def test_acceptance_criteria_p2_text():
    finding = _make_finding(severity="p2")
    item = build_dispatch_item(finding)
    assert item["acceptance_criteria"] == ACCEPTANCE_TEMPLATES["p2"]


def test_acceptance_criteria_p3_text():
    finding = _make_finding(severity="p3")
    item = build_dispatch_item(finding)
    assert item["acceptance_criteria"] == ACCEPTANCE_TEMPLATES["p3"]


def test_stop_condition_p0_mentions_escalate():
    finding = _make_finding(severity="p0")
    item = build_dispatch_item(finding)
    assert "ORCHESTRATOR" in item["stop_condition"]


def test_stop_condition_p1_text():
    finding = _make_finding(severity="p1")
    item = build_dispatch_item(finding)
    assert item["stop_condition"] == STOP_TEMPLATES["p1"]


# ── _infer_rule_id ────────────────────────────────────────────────────────────


def test_infer_rule_id_error_spike():
    finding = {"title": "Error spike after deploy in svc-x"}
    assert _infer_rule_id(finding) == "error-spike-after-deploy"


def test_infer_rule_id_forbidden_dependency():
    finding = {"title": "Forbidden dependency: a → b"}
    assert _infer_rule_id(finding) == "forbidden-dependency-edge"


def test_infer_rule_id_dependency_keyword():
    finding = {"title": "Unexpected dependency observed in production"}
    assert _infer_rule_id(finding) == "forbidden-dependency-edge"


def test_infer_rule_id_exception():
    finding = {"title": "Exception explosion in payments-api"}
    assert _infer_rule_id(finding) == "exception-explosion"


def test_infer_rule_id_drift():
    # "drift" in title, but no "forbidden"/"dependency" prefix — maps to forbidden-edge-drift
    finding = {"title": "Edge drift detected in svc-b"}
    assert _infer_rule_id(finding) == "forbidden-edge-drift"


def test_infer_rule_id_unknown():
    finding = {"title": "Unrecognised rule output"}
    assert _infer_rule_id(finding) == "unknown"


def test_infer_rule_id_empty_title():
    finding = {"title": ""}
    assert _infer_rule_id(finding) == "unknown"


def test_infer_rule_id_missing_title():
    finding = {}
    assert _infer_rule_id(finding) == "unknown"


# ── emit_dispatch ─────────────────────────────────────────────────────────────


def test_emit_dispatch_writes_file(tmp_path):
    findings = [_make_finding()]
    items = emit_dispatch(findings, tmp_path)
    assert (tmp_path / "dispatch_queue.json").exists()
    assert len(items) == 1


def test_emit_dispatch_json_is_valid_list(tmp_path):
    findings = [_make_finding()]
    emit_dispatch(findings, tmp_path)
    loaded = json.loads((tmp_path / "dispatch_queue.json").read_text())
    assert isinstance(loaded, list)
    assert len(loaded) == 1


def test_emit_dispatch_multiple_findings(tmp_path):
    f1 = _make_finding(finding_id="a1111111-1111-1111-1111-111111111111")
    f2 = _make_finding(
        finding_id="a2222222-2222-2222-2222-222222222222",
        title="Exception explosion in svc-a",
        severity="p2",
    )
    items = emit_dispatch([f1, f2], tmp_path)
    assert len(items) == 2
    assert items[0]["finding_id"] == "a1111111-1111-1111-1111-111111111111"
    assert items[1]["finding_id"] == "a2222222-2222-2222-2222-222222222222"


def test_emit_dispatch_stable_ids(tmp_path):
    finding = _make_finding()
    dispatch_ids = [GOLDEN_DISPATCH_ID]
    items = emit_dispatch([finding], tmp_path, dispatch_ids=dispatch_ids)
    assert items[0]["id"] == GOLDEN_DISPATCH_ID


def test_emit_dispatch_creates_output_dir(tmp_path):
    out = tmp_path / "new_subdir"
    assert not out.exists()
    findings = [_make_finding()]
    emit_dispatch(findings, out)
    assert out.exists()
    assert (out / "dispatch_queue.json").exists()


def test_emit_dispatch_created_at_propagated(tmp_path):
    findings = [_make_finding()]
    items = emit_dispatch(findings, tmp_path, created_at="2026-06-17T15:00:00Z")
    assert items[0]["created_at"] == "2026-06-17T15:00:00Z"


def test_emit_dispatch_empty_findings(tmp_path):
    items = emit_dispatch([], tmp_path)
    assert items == []
    loaded = json.loads((tmp_path / "dispatch_queue.json").read_text())
    assert loaded == []


def test_emit_dispatch_all_items_pass_schema(tmp_path):
    f1 = _make_finding(finding_id="a1111111-1111-1111-1111-111111111111")
    f2 = _make_finding(
        finding_id="a2222222-2222-2222-2222-222222222222",
        title="Forbidden dependency: svc-a → svc-b",
        severity="p1",
    )
    items = emit_dispatch([f1, f2], tmp_path)
    for item in items:
        errors = validate_with_schema(item, DISPATCH_SCHEMA)
        assert errors == [], f"Schema errors for {item['finding_id']}: {errors}"
