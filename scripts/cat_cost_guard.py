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

import yaml

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

    try:
        data = yaml.safe_load(text) or {}
    except Exception as exc:
        failures.append(f"FAIL [{rel}]: invalid YAML: {exc}")
        return failures, warnings

    # schedule: trigger check — parse on: key properly.
    # PyYAML (YAML 1.1) parses bare 'on' as the boolean True, so check both.
    on_trigger = data.get(True, data.get("on", {}))
    has_schedule = False
    if isinstance(on_trigger, dict):
        has_schedule = "schedule" in on_trigger
    elif isinstance(on_trigger, list):
        has_schedule = "schedule" in on_trigger
    elif isinstance(on_trigger, str):
        has_schedule = on_trigger == "schedule"

    if has_schedule and "CAT_BUDGET_APPROVED" not in text:
        failures.append(
            f"FAIL [{rel}]: schedule: trigger present without CAT_BUDGET_APPROVED annotation"
        )

    # Risky runner check — inspect per-job runs-on to avoid false positives from comments
    jobs = data.get("jobs", {})
    if isinstance(jobs, dict):
        for job_name, job in jobs.items():
            if isinstance(job, dict):
                runs_on = job.get("runs-on", "")
                if isinstance(runs_on, str) and runs_on in RISKY_RUNNERS:
                    if "CAT_RUNNER_EXCEPTION" not in text:
                        failures.append(
                            f"FAIL [{rel}]: risky runner {runs_on!r} in job {job_name!r} without CAT_RUNNER_EXCEPTION annotation"
                        )

    # Warnings: permissions (top-level or per-job)
    has_top_perms = "permissions" in data
    has_job_perms = isinstance(jobs, dict) and bool(jobs) and all(
        isinstance(j, dict) and "permissions" in j for j in jobs.values()
    )
    if not has_top_perms and not has_job_perms:
        warnings.append(f"WARN [{rel}]: no explicit permissions block")

    # Warnings: concurrency (top-level or per-job)
    has_top_concurrency = "concurrency" in data
    has_job_concurrency = isinstance(jobs, dict) and bool(jobs) and all(
        isinstance(j, dict) and "concurrency" in j for j in jobs.values()
    )
    if not has_top_concurrency and not has_job_concurrency:
        warnings.append(f"WARN [{rel}]: no concurrency block (cancel-in-progress recommended)")

    # Warnings: timeout-minutes (any job)
    has_timeout = isinstance(jobs, dict) and any(
        isinstance(j, dict) and "timeout-minutes" in j for j in jobs.values()
    )
    if not has_timeout:
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

    workflow_files = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    for path in workflow_files:
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

    print(f"cost-guard: all {len(workflow_files)} workflow(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
