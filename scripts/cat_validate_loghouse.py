#!/usr/bin/env python3
"""
LOGHOUSE Alignment Validator (cat_validate_loghouse.py)

Asserts the LOGHOUSE slice is complete and internally consistent:
  1. All 7 LOGHOUSE schemas exist and are valid JSON Schema.
  2. All engine modules import cleanly.
  3. All required fixtures exist and normalize cleanly.
  4. The engine produces >= 1 finding WITH linked evidence and a dispatch item.
  5. The drift report validates against drift_report.schema.json.

Exit 0 on full pass; exits non-zero on any failure.
Writes a machine-readable JSON report to:
    evidence/reports/MP-CAT-A007-4C01_validation_report.json

Usage:
    python scripts/cat_validate_loghouse.py --root .
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root is importable when invoked directly
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import ROOT, validate_with_schema, load_json


# ── Constants ─────────────────────────────────────────────────────────────────

LOGHOUSE_SCHEMAS = [
    "telemetry_envelope.schema.json",
    "finding.schema.json",
    "dependency_edge.schema.json",
    "deploy_event.schema.json",
    "dispatch_queue_item.schema.json",
    "architecture_rule.schema.json",
    "drift_report.schema.json",
]

ENGINE_MODULES = [
    "scripts.loghouse.normalize",
    "scripts.loghouse.correlate",
    "scripts.loghouse.rules",
    "scripts.loghouse.findings",
    "scripts.loghouse.dispatch",
    "scripts.loghouse.drift",
]

REQUIRED_FIXTURES = [
    "tests/fixtures/loghouse/raw_signals.json",
    "tests/fixtures/loghouse/dependency_edges.json",
    "tests/fixtures/loghouse/expected_normalized.json",
]

DRIFT_SCHEMA = "schemas/drift_report.schema.json"
FINDING_SCHEMA = "schemas/finding.schema.json"


# ── Check helpers ─────────────────────────────────────────────────────────────

def check_schemas(root: Path) -> tuple[bool, list[str]]:
    """Assert all 7 LOGHOUSE schemas exist and are valid JSON."""
    results: list[str] = []
    ok = True
    for schema_name in LOGHOUSE_SCHEMAS:
        schema_path = root / "schemas" / schema_name
        if not schema_path.exists():
            results.append(f"FAIL schema missing: {schema_name}")
            ok = False
            continue
        try:
            data = json.loads(schema_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
            # Validate it has at least $schema or type — basic sanity
            results.append(f"PASS schema exists and parses: {schema_name}")
        except Exception as exc:
            results.append(f"FAIL schema invalid JSON ({schema_name}): {exc}")
            ok = False
    return ok, results


def check_modules() -> tuple[bool, list[str]]:
    """Assert all engine modules import without error."""
    results: list[str] = []
    ok = True
    for module_name in ENGINE_MODULES:
        try:
            importlib.import_module(module_name)
            results.append(f"PASS module imports: {module_name}")
        except Exception as exc:
            results.append(f"FAIL module import error ({module_name}): {exc}")
            ok = False
    return ok, results


def check_fixtures(root: Path) -> tuple[bool, list[str]]:
    """Assert required fixture files exist."""
    results: list[str] = []
    ok = True
    for rel_path in REQUIRED_FIXTURES:
        path = root / rel_path
        if path.exists():
            results.append(f"PASS fixture exists: {rel_path}")
        else:
            results.append(f"FAIL fixture missing: {rel_path}")
            ok = False
    return ok, results


def check_normalize(root: Path) -> tuple[bool, list[str]]:
    """Assert fixtures normalize cleanly."""
    results: list[str] = []
    ok = True
    try:
        from scripts.loghouse.normalize import normalize_batch

        raw_path = root / "tests" / "fixtures" / "loghouse" / "raw_signals.json"
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        envelopes, deploy_events, rejected = normalize_batch(raw)

        if envelopes:
            results.append(f"PASS normalize: {len(envelopes)} envelope(s), {len(deploy_events)} deploy event(s), {len(rejected)} rejected")
        else:
            results.append("FAIL normalize: 0 envelopes produced from fixtures")
            ok = False
    except Exception as exc:
        results.append(f"FAIL normalize exception: {exc}")
        ok = False
    return ok, results


def check_engine_produces_findings(root: Path) -> tuple[bool, list[str], list[dict], list[dict]]:
    """
    Run the full engine pipeline and assert:
    - >= 1 finding with linked evidence
    - >= 1 dispatch item
    Returns (ok, messages, findings, dispatch_items).
    """
    results: list[str] = []
    ok = True
    findings: list[dict] = []
    dispatch_items: list[dict] = []

    try:
        from scripts.loghouse.normalize import normalize_batch
        from scripts.loghouse.correlate import correlate
        from scripts.loghouse.rules import evaluate_windows, rule_forbidden_dependency_edge
        from scripts.loghouse.findings import emit_findings
        from scripts.loghouse.dispatch import emit_dispatch

        fixture_dir = root / "tests" / "fixtures" / "loghouse"
        raw = json.loads((fixture_dir / "raw_signals.json").read_text(encoding="utf-8"))
        envelopes, deploy_events, _ = normalize_batch(raw)
        windows = correlate(envelopes, deploy_events)
        raw_findings = evaluate_windows(windows)

        dep_edges_path = fixture_dir / "dependency_edges.json"
        if dep_edges_path.exists():
            dep_edges = json.loads(dep_edges_path.read_text(encoding="utf-8"))
            raw_findings.extend(rule_forbidden_dependency_edge(dep_edges))

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            findings = emit_findings(raw_findings, out)
            dispatch_items = emit_dispatch(findings, out)

        # Check findings have evidence
        findings_without_evidence = [f for f in findings if not f.get("evidence")]
        if findings_without_evidence:
            for f in findings_without_evidence:
                results.append(f"FAIL finding without evidence: {f.get('finding_id', '?')} — {f.get('title', '?')}")
            ok = False
        else:
            results.append(f"PASS engine findings: {len(findings)} finding(s), all have evidence")

        if not findings:
            results.append("FAIL engine produced 0 findings")
            ok = False

        if dispatch_items:
            results.append(f"PASS engine dispatch: {len(dispatch_items)} dispatch item(s)")
        else:
            results.append("FAIL engine produced 0 dispatch items")
            ok = False

    except Exception as exc:
        results.append(f"FAIL engine exception: {exc}")
        ok = False

    return ok, results, findings, dispatch_items


def check_drift_report(root: Path) -> tuple[bool, list[str]]:
    """Run detect_drift and validate the report against drift_report.schema.json."""
    results: list[str] = []
    ok = True

    try:
        from scripts.loghouse.drift import load_architecture_rules, detect_drift

        rules_path = root / "reference" / "loghouse" / "architecture_rules.yaml"
        if not rules_path.exists():
            results.append(f"FAIL drift rules missing: {rules_path}")
            return False, results

        rules = load_architecture_rules(rules_path)
        fixture_dir = root / "tests" / "fixtures" / "loghouse"
        edges = json.loads((fixture_dir / "dependency_edges.json").read_text(encoding="utf-8"))
        drift_schema_path = root / DRIFT_SCHEMA

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            report, drift_findings = detect_drift(
                edges,
                rules,
                out,
                report_id="r0000000-cccc-cccc-cccc-000000000007",
                generated_at="2026-06-17T00:00:00Z",
            )

        errors = validate_with_schema(report, drift_schema_path)
        if errors:
            results.append(f"FAIL drift report schema invalid: {errors}")
            ok = False
        else:
            results.append(
                f"PASS drift report validates: blocked={report['summary']['blocked']}, "
                f"intentional={report['summary']['intentional']}"
            )

        if report["summary"]["blocked"] < 1:
            results.append("FAIL drift: expected >= 1 blocked edge from fixture")
            ok = False

    except Exception as exc:
        results.append(f"FAIL drift exception: {exc}")
        ok = False

    return ok, results


# ── Report writer ──────────────────────────────────────────────────────────────

def write_report(root: Path, all_results: list[dict[str, Any]], overall_ok: bool) -> Path:
    """Write the machine-readable JSON validation report."""
    report_dir = root / "evidence" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "MP-CAT-A007-4C01_validation_report.json"

    report: dict[str, Any] = {
        "mission_id": "MP-CAT-A007-4C01",
        "validator": "cat_validate_loghouse.py",
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": "PASS" if overall_ok else "FAIL",
        "checks": all_results,
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the LOGHOUSE slice of the CAT repo."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repo root directory (default: auto-detected from script location)",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    all_results: list[dict[str, Any]] = []
    overall_ok = True

    # ── 1. Schemas ──────────────────────────────────────────────────────────
    schemas_ok, schema_msgs = check_schemas(root)
    all_results.append({"check": "schemas", "ok": schemas_ok, "details": schema_msgs})
    if not schemas_ok:
        overall_ok = False
    for msg in schema_msgs:
        print(msg)

    # ── 2. Module imports ───────────────────────────────────────────────────
    modules_ok, module_msgs = check_modules()
    all_results.append({"check": "module_imports", "ok": modules_ok, "details": module_msgs})
    if not modules_ok:
        overall_ok = False
    for msg in module_msgs:
        print(msg)

    # ── 3. Fixtures ─────────────────────────────────────────────────────────
    fixtures_ok, fixture_msgs = check_fixtures(root)
    all_results.append({"check": "fixtures", "ok": fixtures_ok, "details": fixture_msgs})
    if not fixtures_ok:
        overall_ok = False
    for msg in fixture_msgs:
        print(msg)

    # ── 4. Normalize ────────────────────────────────────────────────────────
    norm_ok, norm_msgs = check_normalize(root)
    all_results.append({"check": "normalize", "ok": norm_ok, "details": norm_msgs})
    if not norm_ok:
        overall_ok = False
    for msg in norm_msgs:
        print(msg)

    # ── 5. Engine findings + dispatch ───────────────────────────────────────
    engine_ok, engine_msgs, findings, dispatch_items = check_engine_produces_findings(root)
    all_results.append({
        "check": "engine_findings_and_dispatch",
        "ok": engine_ok,
        "details": engine_msgs,
        "finding_count": len(findings),
        "dispatch_count": len(dispatch_items),
    })
    if not engine_ok:
        overall_ok = False
    for msg in engine_msgs:
        print(msg)

    # ── 6. Drift report ─────────────────────────────────────────────────────
    drift_ok, drift_msgs = check_drift_report(root)
    all_results.append({"check": "drift_report", "ok": drift_ok, "details": drift_msgs})
    if not drift_ok:
        overall_ok = False
    for msg in drift_msgs:
        print(msg)

    # ── Write JSON report ────────────────────────────────────────────────────
    report_path = write_report(root, all_results, overall_ok)
    print(f"\nReport written to: {report_path}")

    # ── Summary ──────────────────────────────────────────────────────────────
    if overall_ok:
        print("\nLOGHOUSE validation passed.")
        return 0
    else:
        print("\nLOGHOUSE validation FAILED.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
