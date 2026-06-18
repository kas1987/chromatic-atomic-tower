#!/usr/bin/env python3
"""CAT GitHub Actions cost guard.

Blocks risky workflow patterns unless explicitly approved:
- schedule: triggers without CAT_BUDGET_APPROVED annotation
- windows-latest or macos-latest runners without CAT_RUNNER_EXCEPTION annotation
- Missing explicit permissions block (warning only)
- Missing concurrency block (warning only)
- Missing timeout-minutes (warning only)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
RISKY_RUNNERS = ["windows-latest", "macos-latest"]


def check_workflow(path: Path) -> tuple[list[str], list[str]]:
    """Returns (failures, warnings) for a single workflow file."""
    failures: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"{path.name}: cannot read file: {exc}")
        return failures, warnings

    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = path.name

    if "schedule:" in text and "CAT_BUDGET_APPROVED" not in text:
        failures.append(
            f"FAIL [{rel}]: schedule: trigger present without CAT_BUDGET_APPROVED annotation"
        )

    for runner in RISKY_RUNNERS:
        if runner in text and "CAT_RUNNER_EXCEPTION" not in text:
            failures.append(
                f"FAIL [{rel}]: risky runner {runner!r} without CAT_RUNNER_EXCEPTION annotation"
            )

    if "permissions:" not in text:
        warnings.append(f"WARN [{rel}]: no explicit permissions block")

    if "concurrency:" not in text:
        warnings.append(f"WARN [{rel}]: no concurrency block (cancel-in-progress recommended)")

    if "timeout-minutes:" not in text:
        warnings.append(f"WARN [{rel}]: no timeout-minutes on any job")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="CAT GitHub Actions cost guard.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check all workflows and exit nonzero if any failures found.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures.",
    )
    args = parser.parse_args()

    if not WORKFLOWS.exists():
        print("No .github/workflows directory found; pass.")
        return 0

    all_failures: list[str] = []
    all_warnings: list[str] = []

    for path in sorted(WORKFLOWS.glob("*.yml")):
        f, w = check_workflow(path)
        all_failures.extend(f)
        all_warnings.extend(w)

    for warn in all_warnings:
        print(warn)

    for fail in all_failures:
        print(fail)

    if args.strict:
        all_failures.extend(all_warnings)

    if all_failures:
        print(f"\ncost-guard: {len(all_failures)} failure(s) found.")
        return 1

    print(f"cost-guard: all {len(list(WORKFLOWS.glob('*.yml')))} workflow(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
