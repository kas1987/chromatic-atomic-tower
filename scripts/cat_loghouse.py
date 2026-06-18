#!/usr/bin/env python3
"""
LOGHOUSE CLI (cat_loghouse.py)

Two modes:

External mode (default): runs the pipeline over a fixture/signal directory.
    python scripts/cat_loghouse.py --input tests/fixtures/loghouse --output /tmp/loghouse/output

Self-monitoring mode: reads CAT's own operational JSONL logs as telemetry.
    python scripts/cat_loghouse.py --mode self [--strict] [--output /tmp/loghouse/self]

--strict (self mode only): exit non-zero if any P0 or P1 finding is emitted.
Without --strict, findings are advisory and the exit code is always 0 on success.
Zero findings in self mode is normal (no governance anomalies detected).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path when run as a script (not via -m)
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.common import ROOT
from scripts.loghouse.normalize import normalize_batch
from scripts.loghouse.correlate import correlate
from scripts.loghouse.rules import evaluate_windows, rule_forbidden_dependency_edge
from scripts.loghouse.findings import emit_findings
from scripts.loghouse.dispatch import emit_dispatch

CRITICAL_SEVERITIES = {"p0", "p1"}


def run_pipeline(input_dir: Path, output_dir: Path) -> int:
    """
    Run the LOGHOUSE pipeline over a fixture directory.
    Returns exit code: 0 = success, 1 = error or no findings.
    """
    print(f"[loghouse] Input:  {input_dir}")
    print(f"[loghouse] Output: {output_dir}")

    raw_signals_path = input_dir / "raw_signals.json"
    if not raw_signals_path.exists():
        print(f"[loghouse] ERROR: {raw_signals_path} not found", file=sys.stderr)
        return 1

    raw = json.loads(raw_signals_path.read_text())
    print(f"[loghouse] Loaded {len(raw)} raw signals from {raw_signals_path}")

    envelopes, deploy_events, rejected = normalize_batch(raw)
    print(
        f"[loghouse] Normalized: {len(envelopes)} envelopes, "
        f"{len(deploy_events)} deploy events, {len(rejected)} rejected"
    )

    windows = correlate(envelopes, deploy_events)
    print(f"[loghouse] Correlated into {len(windows)} window(s)")

    raw_findings = evaluate_windows(windows)

    dep_edges_path = input_dir / "dependency_edges.json"
    if dep_edges_path.exists():
        dep_edges = json.loads(dep_edges_path.read_text())
        print(f"[loghouse] Loaded {len(dep_edges)} dependency edges")
        raw_findings.extend(rule_forbidden_dependency_edge(dep_edges))

    print(f"[loghouse] Rules produced {len(raw_findings)} raw finding(s)")

    validated_findings = emit_findings(raw_findings, output_dir)
    dispatch_items = emit_dispatch(validated_findings, output_dir)

    print(
        f"[loghouse] Pipeline complete: {len(validated_findings)} finding(s), "
        f"{len(dispatch_items)} dispatch item(s)"
    )

    if not validated_findings:
        print("[loghouse] WARNING: No findings emitted", file=sys.stderr)
        return 1

    if not dispatch_items:
        print("[loghouse] WARNING: No dispatch items emitted", file=sys.stderr)
        return 1

    return 0


def run_self_pipeline(output_dir: Path, *, strict: bool) -> int:
    """
    Run LOGHOUSE in self-monitoring mode using CAT's own operational JSONL logs.
    Returns exit code: 0 = clean (or no critical findings), 1 = P0/P1 found (strict).
    Zero findings is the happy path — no anomalies detected.
    """
    from scripts.loghouse.cat_adapter import load_cat_signals

    print("[loghouse:self] Loading CAT operational signals via cat_adapter…")
    raw = load_cat_signals()
    print(f"[loghouse:self] Loaded {len(raw)} raw signals from CAT logs")

    envelopes, deploy_events, rejected = normalize_batch(raw)
    print(
        f"[loghouse:self] Normalized: {len(envelopes)} envelopes, "
        f"{len(deploy_events)} deploy events, {len(rejected)} rejected"
    )
    if rejected:
        for r in rejected[:5]:
            print(f"  REJECTED: {r.get('errors')} — {str(r.get('raw', {}))[:80]}", file=sys.stderr)

    windows = correlate(envelopes, deploy_events)
    print(f"[loghouse:self] Correlated into {len(windows)} window(s)")

    raw_findings = evaluate_windows(windows)
    print(f"[loghouse:self] Rules produced {len(raw_findings)} raw finding(s)")

    validated_findings = emit_findings(raw_findings, output_dir)
    dispatch_items = emit_dispatch(validated_findings, output_dir)

    critical = [f for f in validated_findings if f.get("severity") in CRITICAL_SEVERITIES]

    print(
        f"[loghouse:self] Complete: {len(validated_findings)} finding(s) "
        f"({len(critical)} critical), {len(dispatch_items)} dispatch item(s)"
    )

    if critical:
        print("\n[loghouse:self] CRITICAL FINDINGS:", file=sys.stderr)
        for f in critical:
            print(f"  [{f['severity'].upper()}] {f['title']}", file=sys.stderr)
        if strict:
            print("[loghouse:self] Exiting non-zero (--strict, critical findings present)", file=sys.stderr)
            return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="LOGHOUSE pipeline CLI")
    parser.add_argument(
        "--mode",
        choices=["external", "self"],
        default="external",
        help="'external' (default): run over --input fixture dir. 'self': monitor CAT's own logs.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "loghouse",
        help="[external mode] Input directory containing raw_signals.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "loghouse",
        help="Output directory for findings.json, findings.md, dispatch_queue.json",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="[self mode] Exit non-zero if any P0/P1 finding is emitted.",
    )
    args = parser.parse_args()

    if args.mode == "self":
        exit_code = run_self_pipeline(args.output, strict=args.strict)
    else:
        exit_code = run_pipeline(args.input, args.output)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
