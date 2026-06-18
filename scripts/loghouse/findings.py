"""
LOGHOUSE Findings Engine.

Validates raw finding dicts against finding.schema.json and emits:
- findings.json (list of validated findings)
- findings.md (Markdown report)

Evidence-first: findings without evidence are dropped.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from scripts.common import ROOT, validate_with_schema

FINDING_SCHEMA = ROOT / "schemas" / "finding.schema.json"

STATIC_FINDING_ID = "f0000000-0000-0000-0000-000000000001"  # for golden tests only


def build_finding(raw: dict[str, Any], finding_id: str | None = None) -> dict[str, Any]:
    """
    Construct a finding record from a raw rule output.
    Assigns a stable ID if provided, otherwise generates a UUID.
    """
    evidence = raw.get("evidence", [])
    if not evidence:
        raise ValueError(f"Finding '{raw.get('title', '?')}' has no evidence — cannot emit.")

    return {
        "finding_id": finding_id or str(uuid.uuid4()),
        "title": raw["title"],
        "category": raw["category"],
        "severity": raw["severity"],
        "confidence": raw["confidence"],
        "status": "open",
        "services": raw["services"],
        "first_seen": raw["first_seen"],
        "last_seen": raw["last_seen"],
        "owner": raw["owner"],
        "hypothesis": raw["hypothesis"],
        "suggested_fix": raw["suggested_fix"],
        "blast_radius": raw["blast_radius"],
        "sla_impact": raw["sla_impact"],
        "evidence": evidence,
    }


def emit_findings(
    raw_findings: list[dict[str, Any]],
    output_dir: Path,
    *,
    finding_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Validate each raw finding, write findings.json and findings.md to output_dir.

    Returns the list of validated finding records.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    validated: list[dict[str, Any]] = []

    for i, raw in enumerate(raw_findings):
        fid = (finding_ids[i] if finding_ids and i < len(finding_ids) else None)
        try:
            finding = build_finding(raw, finding_id=fid)
        except ValueError as exc:
            print(f"[findings] SKIP — {exc}")
            continue

        errors = validate_with_schema(finding, FINDING_SCHEMA)
        if errors:
            print(f"[findings] SCHEMA ERRORS in '{finding.get('title')}': {errors}")
            continue

        validated.append(finding)

    findings_json = output_dir / "findings.json"
    findings_json.write_text(json.dumps(validated, indent=2), encoding="utf-8")

    findings_md = output_dir / "findings.md"
    findings_md.write_text(_render_markdown(validated), encoding="utf-8")

    print(f"[findings] Emitted {len(validated)} finding(s) to {output_dir}")
    return validated


def _render_markdown(findings: list[dict[str, Any]]) -> str:
    lines = ["# LOGHOUSE Findings Report\n"]
    if not findings:
        lines.append("No findings detected.\n")
        return "\n".join(lines)

    for f in findings:
        lines.append(f"## {f['title']}")
        lines.append(f"- **finding_id**: `{f['finding_id']}`")
        lines.append(f"- **severity**: {f['severity']}")
        lines.append(f"- **category**: {f['category']}")
        lines.append(f"- **confidence**: {f['confidence']}")
        lines.append(f"- **owner**: {f['owner']}")
        lines.append(f"- **services**: {', '.join(f['services'])}")
        lines.append(f"- **status**: {f['status']}")
        lines.append(f"- **first_seen**: {f['first_seen']}")
        lines.append(f"- **last_seen**: {f['last_seen']}")
        lines.append(f"\n**Hypothesis**: {f['hypothesis']}")
        lines.append(f"\n**Suggested Fix**: {f['suggested_fix']}")
        lines.append("\n**Evidence**:")
        for ev in f["evidence"]:
            lines.append(f"  - [{ev['source_type']}] `{ev['source_ref']}` at {ev['observed_at']}: {ev['summary']}")
        lines.append("")

    return "\n".join(lines)
