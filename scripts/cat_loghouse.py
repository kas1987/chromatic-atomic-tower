#!/usr/bin/env python3
"""
LOGHOUSE CLI (cat_loghouse.py)

Runs the full LOGHOUSE pipeline over an input fixture directory:
  normalize → correlate → rules → findings → dispatch

Usage:
    python scripts/cat_loghouse.py --input tests/fixtures/loghouse --output /tmp/loghouse/output
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


def run_pipeline(input_dir: Path, output_dir: Path) -> int:
    """
    Run the full LOGHOUSE pipeline.

    Returns exit code: 0 = success, 1 = error.
    """
    print(f"[loghouse] Input:  {input_dir}")
    print(f"[loghouse] Output: {output_dir}")

    # Step 1: Load raw signals
    raw_signals_path = input_dir / "raw_signals.json"
    if not raw_signals_path.exists():
        print(f"[loghouse] ERROR: {raw_signals_path} not found", file=sys.stderr)
        return 1

    raw = json.loads(raw_signals_path.read_text())
    print(f"[loghouse] Loaded {len(raw)} raw signals from {raw_signals_path}")

    # Step 2: Normalize
    envelopes, deploy_events, rejected = normalize_batch(raw)
    print(
        f"[loghouse] Normalized: {len(envelopes)} envelopes, "
        f"{len(deploy_events)} deploy events, {len(rejected)} rejected"
    )

    # Step 3: Correlate
    windows = correlate(envelopes, deploy_events)
    print(f"[loghouse] Correlated into {len(windows)} window(s)")

    # Step 4: Rules
    raw_findings = evaluate_windows(windows)

    # Also check dependency edges if present
    dep_edges_path = input_dir / "dependency_edges.json"
    if dep_edges_path.exists():
        dep_edges = json.loads(dep_edges_path.read_text())
        print(f"[loghouse] Loaded {len(dep_edges)} dependency edges")
        raw_findings.extend(rule_forbidden_dependency_edge(dep_edges))

    print(f"[loghouse] Rules produced {len(raw_findings)} raw finding(s)")

    # Step 5: Emit findings
    validated_findings = emit_findings(raw_findings, output_dir)

    # Step 6: Emit dispatch items
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


def main() -> None:
    parser = argparse.ArgumentParser(description="LOGHOUSE pipeline CLI")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "loghouse",
        help="Input directory containing raw_signals.json (and optionally dependency_edges.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "loghouse",
        help="Output directory for findings.json, findings.md, dispatch_queue.json "
        "(defaults to the OS temp dir so manual runs never pollute the repo root)",
    )
    args = parser.parse_args()

    exit_code = run_pipeline(args.input, args.output)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
