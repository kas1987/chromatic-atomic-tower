"""
LOGHOUSE Drift Detector.

Compares observed dependency_edge records against architecture rules,
classifies each edge as: intentional | accidental | blocked | unknown,
and emits a drift_report.schema.json-valid report.

Blocked edges produce findings via the findings engine.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from scripts.common import ROOT, validate_with_schema, load_yaml
from scripts.loghouse.rules import rule_forbidden_dependency_edge
from scripts.loghouse.findings import emit_findings, build_finding

DRIFT_SCHEMA = ROOT / "schemas" / "drift_report.schema.json"
ARCH_RULE_SCHEMA = ROOT / "schemas" / "architecture_rule.schema.json"
EDGE_SCHEMA = ROOT / "schemas" / "dependency_edge.schema.json"

STATIC_REPORT_ID = "r0000000-0000-0000-0000-000000000001"  # for golden tests only


def load_architecture_rules(rules_path: Path) -> list[dict[str, Any]]:
    """Load and validate architecture rules from YAML."""
    data = load_yaml(rules_path)
    rules = data.get("rules", [])
    for rule in rules:
        errors = validate_with_schema(rule, ARCH_RULE_SCHEMA)
        if errors:
            raise ValueError(f"Invalid architecture rule {rule.get('rule_id')}: {errors}")
    return rules


def _edge_matches_rule(edge: dict[str, Any], rule: dict[str, Any]) -> bool:
    """Check if an observed edge matches a rule's source/target/edge_type."""
    source_match = edge.get("source") == rule.get("source") or rule.get("source") == "*"
    target_match = edge.get("target") == rule.get("target") or rule.get("target") == "*"
    type_match = rule.get("edge_type") in (edge.get("edge_type"), "any")
    return source_match and target_match and type_match


def classify_edge(
    edge: dict[str, Any],
    rules: list[dict[str, Any]],
) -> tuple[str, str | None]:
    """
    Classify an observed edge against the rule set.

    Returns (classification, rule_id):
    - intentional: explicitly allowed by a rule
    - blocked:     explicitly forbidden by a rule
    - accidental:  edge.allowed is False but no matching rule
    - unknown:     no matching rule and edge.allowed is True or unspecified
    """
    for rule in rules:
        if _edge_matches_rule(edge, rule):
            if rule["decision"] == "allowed":
                return "intentional", rule["rule_id"]
            elif rule["decision"] == "forbidden":
                return "blocked", rule["rule_id"]

    # No rule matched
    if edge.get("allowed") is False:
        return "accidental", None
    return "unknown", None


def detect_drift(
    edges: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    output_dir: Path,
    *,
    report_id: str | None = None,
    generated_at: str | None = None,
    finding_ids: list[str] | None = None,
    dispatch_ids: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Classify all observed edges against rules and produce a drift report.

    Blocked edges also produce findings via the findings engine.

    Returns (drift_report, findings).
    """
    from scripts.loghouse.dispatch import emit_dispatch

    classified_edges: list[dict[str, Any]] = []
    blocked_edges: list[dict[str, Any]] = []
    counts = {"intentional": 0, "accidental": 0, "blocked": 0, "unknown": 0}

    for edge in edges:
        classification, rule_id = classify_edge(edge, rules)
        counts[classification] += 1

        edge_entry: dict[str, Any] = {
            "edge_id": edge["edge_id"],
            "source": edge["source"],
            "target": edge["target"],
            "edge_type": edge["edge_type"],
            "classification": classification,
        }
        if rule_id:
            edge_entry["rule_id"] = rule_id

        classified_edges.append(edge_entry)

        if classification == "blocked":
            blocked_edges.append(edge)

    # Produce findings for blocked edges
    findings: list[dict[str, Any]] = []
    finding_records: list[dict[str, Any]] = []

    if blocked_edges:
        raw_findings = rule_forbidden_dependency_edge(blocked_edges)
        output_dir.mkdir(parents=True, exist_ok=True)
        finding_records = emit_findings(raw_findings, output_dir, finding_ids=finding_ids)
        findings = finding_records

        # Annotate edge entries with finding_ids
        finding_idx = 0
        for edge_entry in classified_edges:
            if edge_entry["classification"] == "blocked" and finding_idx < len(finding_records):
                edge_entry["finding_id"] = finding_records[finding_idx]["finding_id"]
                finding_idx += 1

    report: dict[str, Any] = {
        "report_id": report_id or str(uuid.uuid4()),
        "generated_at": generated_at or "1970-01-01T00:00:00Z",
        "edges": classified_edges,
        "summary": {
            "intentional": counts["intentional"],
            "accidental": counts["accidental"],
            "blocked": counts["blocked"],
            "unknown": counts["unknown"],
            "total": len(edges),
        },
    }

    # Validate the report
    errors = validate_with_schema(report, DRIFT_SCHEMA)
    if errors:
        raise ValueError(f"Drift report schema errors: {errors}")

    # Write report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "drift_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[drift] Report written to {report_path} — {counts}")
    return report, findings
