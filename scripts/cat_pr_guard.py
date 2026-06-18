#!/usr/bin/env python3
"""CAT GitHub PR and Issue Bridge guard.

Validates that PR bodies and issue templates contain required CAT fields:
- Mission ID matching MP-CAT-... pattern
- BEAD ID matching BEAD-CAT-... pattern
- Evidence path reference
- Validation checklist present

Modes:
  --check-pr <body>      Validate a PR body string against CAT requirements
  --check-samples        Run built-in pass/fail samples; exits nonzero on mismatch
  --check-templates      Check that required template files exist
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MISSION_ID_PATTERN = re.compile(r'MP-CAT-[A-Z][0-9]{3}-[1-4]C[0-9]{2}')
BEAD_ID_PATTERN = re.compile(r'BEAD-CAT-[A-Z][0-9]{3}-[1-4]C[0-9]{2}-[0-9]{2}')
EVIDENCE_PATTERN = re.compile(r'evidence/')

REQUIRED_TEMPLATES = [
    '.github/pull_request_template.md',
    '.github/ISSUE_TEMPLATE/mission_request.md',
    '.github/ISSUE_TEMPLATE/bead_task.md',
]

SAMPLE_PASS = """\
## Mission

Mission ID: MP-CAT-A014-4C01

## BEAD

BEAD ID: BEAD-CAT-A014-4C01-05

## Evidence

Evidence path: evidence/reports/pr-guard-pytest-output.txt
"""

SAMPLE_FAIL_NO_MISSION = """\
## Summary

Some changes without mission or bead ids.
"""

SAMPLE_FAIL_NO_BEAD = """\
## Mission

Mission ID: MP-CAT-A014-4C01

## Evidence

Evidence path: evidence/reports/pr-guard-pytest-output.txt
"""


def check_pr_body(body: str) -> list[str]:
    """Return list of validation errors for a PR body."""
    errors: list[str] = []
    if not MISSION_ID_PATTERN.search(body):
        errors.append("missing Mission ID (expected format: MP-CAT-XXXX-XCXX)")
    if not BEAD_ID_PATTERN.search(body):
        errors.append("missing BEAD ID (expected format: BEAD-CAT-XXXX-XCXX-NN)")
    if not EVIDENCE_PATTERN.search(body):
        errors.append("missing evidence path reference (expected: evidence/...)")
    return errors


def check_templates() -> list[str]:
    """Return list of missing required template files."""
    missing = []
    for rel in REQUIRED_TEMPLATES:
        if not (ROOT / rel).exists():
            missing.append(f"missing template: {rel}")
    return missing


def run_samples() -> int:
    """Run built-in pass/fail samples. Returns 0 on success, 1 on mismatch."""
    ok = True

    errors = check_pr_body(SAMPLE_PASS)
    if errors:
        print(f"FAIL: SAMPLE_PASS should have no errors, got: {errors}")
        ok = False
    else:
        print("PASS: SAMPLE_PASS validated correctly (no errors)")

    errors = check_pr_body(SAMPLE_FAIL_NO_MISSION)
    if not any('Mission ID' in e for e in errors):
        print("FAIL: SAMPLE_FAIL_NO_MISSION should report missing Mission ID")
        ok = False
    else:
        print("PASS: SAMPLE_FAIL_NO_MISSION correctly rejected (missing Mission ID)")

    errors = check_pr_body(SAMPLE_FAIL_NO_BEAD)
    if not any('BEAD ID' in e for e in errors):
        print("FAIL: SAMPLE_FAIL_NO_BEAD should report missing BEAD ID")
        ok = False
    else:
        print("PASS: SAMPLE_FAIL_NO_BEAD correctly rejected (missing BEAD ID)")

    template_errors = check_templates()
    if template_errors:
        for e in template_errors:
            print(f"FAIL: {e}")
        ok = False
    else:
        print(f"PASS: all {len(REQUIRED_TEMPLATES)} required templates present")

    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="CAT PR and Issue Bridge guard.")
    parser.add_argument('--check-samples', action='store_true',
                        help="Run built-in pass/fail samples and validate.")
    parser.add_argument('--check-pr', metavar='BODY',
                        help="Validate a PR body string.")
    parser.add_argument('--check-templates', action='store_true',
                        help="Check that required template files exist.")
    args = parser.parse_args()

    if args.check_samples:
        return run_samples()

    if args.check_pr:
        errors = check_pr_body(args.check_pr)
        for e in errors:
            print(f"FAIL: {e}")
        if not errors:
            print("PASS: PR body is valid")
        return 1 if errors else 0

    if args.check_templates:
        missing = check_templates()
        for m in missing:
            print(f"FAIL: {m}")
        if not missing:
            print(f"PASS: all {len(REQUIRED_TEMPLATES)} required templates present")
        return 1 if missing else 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
