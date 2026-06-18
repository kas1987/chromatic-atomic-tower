"""
LOGHOUSE Dispatch Writer.

Converts validated findings into dispatch_queue_item-valid records.
Each dispatch item is agent-routable with owner, evidence reference,
acceptance criteria, and stop condition.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from scripts.common import ROOT, validate_with_schema

DISPATCH_SCHEMA = ROOT / "schemas" / "dispatch_queue_item.schema.json"

STATIC_DISPATCH_ID = "d0000000-0000-0000-0000-000000000001"  # for golden tests only

# Rule → agent_role mapping
RULE_TO_AGENT: dict[str, str] = {
    "error-spike-after-deploy": "BUILDER",
    "forbidden-dependency-edge": "AUDITOR",
    "exception-explosion": "BUILDER",
    "forbidden-edge-drift": "AUDITOR",
}

# Severity → acceptance criteria templates
ACCEPTANCE_TEMPLATES: dict[str, str] = {
    "p0": "Critical issue resolved: error rate returns to baseline within 15 minutes and root cause documented.",
    "p1": "High-priority issue mitigated: error rate returns below 1% within 30 minutes of action taken.",
    "p2": "Issue investigated: root cause identified and fix plan documented within 4 hours.",
    "p3": "Issue logged: tracked in backlog with severity assessment completed.",
}

STOP_TEMPLATES: dict[str, str] = {
    "p0": "Stop immediately if remediation requires schema migration, data deletion, or production credential rotation — escalate to ORCHESTRATOR.",
    "p1": "Stop if rollback would affect more than one service or requires coordination across teams — escalate to ORCHESTRATOR.",
    "p2": "Stop if root cause is unclear after 2 hours of investigation — escalate to REVIEWER for second opinion.",
    "p3": "Stop if issue is out of scope for the assigned agent role — reassign via ORCHESTRATOR.",
}


def build_dispatch_item(
    finding: dict[str, Any],
    dispatch_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a dispatch_queue_item record from a validated finding."""
    rule_id = _infer_rule_id(finding)
    agent_role = RULE_TO_AGENT.get(rule_id, "REVIEWER")
    severity = finding.get("severity", "p3")
    evidence_ref = finding["evidence"][0]["source_ref"]

    item: dict[str, Any] = {
        "id": dispatch_id or str(uuid.uuid4()),
        "finding_id": finding["finding_id"],
        "owner": finding["owner"],
        "agent_role": agent_role,
        "evidence_ref": evidence_ref,
        "acceptance_criteria": ACCEPTANCE_TEMPLATES.get(severity, ACCEPTANCE_TEMPLATES["p3"]),
        "stop_condition": STOP_TEMPLATES.get(severity, STOP_TEMPLATES["p3"]),
        "priority": severity,
        "status": "queued",
    }
    if created_at:
        item["created_at"] = created_at

    return item


def _infer_rule_id(finding: dict[str, Any]) -> str:
    """Infer the originating rule_id from the finding title/category."""
    title = finding.get("title", "").lower()
    if "error spike" in title:
        return "error-spike-after-deploy"
    if "forbidden" in title or "dependency" in title:
        return "forbidden-dependency-edge"
    if "exception" in title:
        return "exception-explosion"
    if "drift" in title:
        return "forbidden-edge-drift"
    return "unknown"


def emit_dispatch(
    findings: list[dict[str, Any]],
    output_dir: Path,
    *,
    dispatch_ids: list[str] | None = None,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convert findings to dispatch queue items, validate, and write dispatch_queue.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []

    for i, finding in enumerate(findings):
        did = (dispatch_ids[i] if dispatch_ids and i < len(dispatch_ids) else None)
        item = build_dispatch_item(finding, dispatch_id=did, created_at=created_at)

        errors = validate_with_schema(item, DISPATCH_SCHEMA)
        if errors:
            print(f"[dispatch] SCHEMA ERRORS for finding '{finding.get('finding_id')}': {errors}")
            continue

        items.append(item)

    dispatch_json = output_dir / "dispatch_queue.json"
    dispatch_json.write_text(json.dumps(items, indent=2), encoding="utf-8")

    print(f"[dispatch] Emitted {len(items)} dispatch item(s) to {output_dir}")
    return items
