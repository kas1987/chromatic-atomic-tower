#!/usr/bin/env python3
"""Deterministic CAT GitHub Actions cost and hardening guard."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
POLICY_PATH = ROOT / "gates" / "ci" / "COST_GUARD_POLICY.yaml"
RISKY_RUNNERS = {"windows-latest", "macos-latest"}
TIERS = {"none", "balanced", "strict"}


def _git_value(*args: str, default: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=5, check=False
        )
        value = result.stdout.strip()
        return value or default
    except (OSError, subprocess.SubprocessError):
        return default


def _repository_identity() -> str:
    configured = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if configured:
        return configured
    remote = _git_value("config", "--get", "remote.origin.url", default="")
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("https://github.com/"):
        return remote.removeprefix("https://github.com/")
    if remote.startswith("git@github.com:"):
        return remote.removeprefix("git@github.com:")
    return remote or "local"


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    """Load and structurally validate the versioned policy contract."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read policy {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid policy YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("cost-guard policy must be a mapping")
    required = {"version", "default_tier", "rules", "tiers"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"cost-guard policy missing required keys: {', '.join(missing)}")
    if data["default_tier"] not in TIERS:
        raise ValueError(f"invalid policy default_tier: {data['default_tier']!r}")
    rules = data["rules"]
    tiers = data["tiers"]
    if not isinstance(rules, dict) or not rules:
        raise ValueError("cost-guard policy rules must be a non-empty mapping")
    if not isinstance(tiers, dict) or set(tiers) != TIERS:
        raise ValueError("cost-guard policy must define exactly none, balanced, and strict tiers")
    rule_ids = set(rules)
    for rule_id, rule in rules.items():
        if not isinstance(rule, dict) or not rule.get("description") or not rule.get("category"):
            raise ValueError(f"rule {rule_id!r} must define category and description")
    for tier, tier_data in tiers.items():
        actions = tier_data.get("actions") if isinstance(tier_data, dict) else None
        if not isinstance(actions, dict) or set(actions) != rule_ids:
            raise ValueError(f"tier {tier!r} must define an action for every rule")
        if any(action not in {"block", "warn"} for action in actions.values()):
            raise ValueError(f"tier {tier!r} actions must be block or warn")
    return data


def resolve_tier(cli_tier: str | None = None, *, env: dict[str, str] | None = None,
                 policy: dict[str, Any] | None = None) -> str:
    """Resolve CLI > environment > versioned policy default."""
    selected = cli_tier
    if selected is None:
        selected = (env or os.environ).get("CAT_COST_GUARD_TIER")
    if selected is None:
        selected = (policy or load_policy()).get("default_tier")
    selected = str(selected).strip().lower()
    if selected not in TIERS:
        raise ValueError(f"invalid cost-guard tier {selected!r}; expected none, balanced, or strict")
    return selected


def _on_trigger(data: dict[str, Any]) -> Any:
    return data.get(True, data.get("on", {}))


def evaluate_workflow(path: Path, *, tier: str, policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one explainable result for each policy rule on a workflow."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{path.name}: cannot read workflow: {exc}") from exc
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: workflow YAML must be a mapping")

    on_trigger = _on_trigger(data)
    has_schedule = isinstance(on_trigger, dict) and "schedule" in on_trigger
    if isinstance(on_trigger, list):
        has_schedule = "schedule" in on_trigger
    elif isinstance(on_trigger, str):
        has_schedule = on_trigger == "schedule"
    jobs = data.get("jobs", {}) or {}
    if not isinstance(jobs, dict):
        raise ValueError(f"{path.name}: jobs must be a mapping")

    risky_jobs = [
        job_name for job_name, job in jobs.items()
        if isinstance(job, dict) and job.get("runs-on") in RISKY_RUNNERS
    ]
    has_permissions = "permissions" in data or (
        bool(jobs) and all(isinstance(job, dict) and "permissions" in job for job in jobs.values())
    )
    has_concurrency = "concurrency" in data or (
        bool(jobs) and all(isinstance(job, dict) and "concurrency" in job for job in jobs.values())
    )
    missing_timeout_jobs = [
        job_name for job_name, job in jobs.items()
        if isinstance(job, dict) and "timeout-minutes" not in job
    ]
    triggered = {
        "schedule_budget_approval": has_schedule and "CAT_BUDGET_APPROVED" not in text,
        "risky_runner_exception": bool(risky_jobs) and "CAT_RUNNER_EXCEPTION" not in text,
        "explicit_permissions": not has_permissions,
        "concurrency": not has_concurrency,
        "job_timeout": bool(missing_timeout_jobs),
    }
    details = {
        "schedule_budget_approval": "schedule trigger requires CAT_BUDGET_APPROVED annotation",
        "risky_runner_exception": f"risky runner jobs require CAT_RUNNER_EXCEPTION annotation: {risky_jobs} ({', '.join(sorted({str(jobs[name].get('runs-on')) for name in risky_jobs}))})",
        "explicit_permissions": "workflow requires an explicit permissions block",
        "concurrency": "workflow requires a concurrency block",
        "job_timeout": f"jobs require timeout-minutes: {missing_timeout_jobs}",
    }
    actions = policy["tiers"][tier]["actions"]
    return [
        {
            "rule_id": rule_id,
            "category": rule["category"],
            "description": rule["description"],
            "status": "fail" if triggered[rule_id] else "pass",
            "action": actions[rule_id] if triggered[rule_id] else "pass",
            "message": details[rule_id] if triggered[rule_id] else "rule satisfied",
        }
        for rule_id, rule in policy["rules"].items()
    ]


def check_workflow(path: Path, tier: str | None = None, policy: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    """Return (blocking failures, advisory warnings) for compatibility callers."""
    policy = policy or load_policy()
    selected_tier = resolve_tier(tier, policy=policy)
    try:
        results = evaluate_workflow(path, tier=selected_tier, policy=policy)
    except ValueError as exc:
        return [f"FAIL [evaluator]: {exc}"], []
    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = path.name
    failures = [f"FAIL [{rel}] [{r['rule_id']}]: {r['message']}" for r in results if r["status"] == "fail" and r["action"] == "block"]
    warnings = [f"WARN [{rel}] [{r['rule_id']}]: {r['message']}" for r in results if r["status"] == "fail" and r["action"] == "warn"]
    return failures, warnings


def build_report(workflow_files: list[Path], *, tier: str, policy: dict[str, Any], output_path: str = "") -> tuple[dict[str, Any], list[str], list[str]]:
    all_failures: list[str] = []
    all_warnings: list[str] = []
    workflow_reports: list[dict[str, Any]] = []
    evaluator_errors: list[str] = []
    for path in workflow_files:
        try:
            results = evaluate_workflow(path, tier=tier, policy=policy)
            failures, warnings = check_workflow(path, tier=tier, policy=policy)
        except ValueError as exc:
            evaluator_errors.append(str(exc))
            continue
        workflow_reports.append({"workflow": str(path.relative_to(ROOT)), "rules": results})
        all_failures.extend(failures)
        all_warnings.extend(warnings)
    report = {
        "schema_version": "1.0.0",
        "policy_version": str(policy["version"]),
        "tier": tier,
        "repository": _repository_identity(),
        "head_sha": _git_value("rev-parse", "HEAD"),
        "default_branch": _git_value("symbolic-ref", "refs/remotes/origin/HEAD", default="unknown").removeprefix("refs/remotes/origin/"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_path": output_path or None,
        "summary": {
            "workflow_count": len(workflow_files),
            "failure_count": len(all_failures),
            "warning_count": len(all_warnings),
            "evaluator_error_count": len(evaluator_errors),
        },
        "workflows": workflow_reports,
        "failures": all_failures,
        "warnings": all_warnings,
        "evaluator_errors": evaluator_errors,
    }
    return report, all_failures + evaluator_errors, all_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="CAT GitHub Actions cost and hardening guard.")
    parser.add_argument("--check", action="store_true", help="Check all workflows.")
    parser.add_argument("--tier", choices=sorted(TIERS), help="Policy tier.")
    parser.add_argument("--strict", action="store_true", help="Legacy alias for --tier strict.")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON evidence.")
    parser.add_argument("--output", help="Write JSON evidence to this path.")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH, help="Policy YAML path.")
    args = parser.parse_args()
    if args.strict and args.tier and args.tier != "strict":
        parser.error("--strict conflicts with --tier other than strict")
    cli_tier = "strict" if args.strict else args.tier
    try:
        policy = load_policy(args.policy)
        tier = resolve_tier(cli_tier, policy=policy)
    except ValueError as exc:
        print(f"cost-guard evaluator error: {exc}", file=sys.stderr)
        return 2
    if not WORKFLOWS.exists():
        report = {"schema_version": "1.0.0", "policy_version": str(policy["version"]), "tier": tier, "summary": {"workflow_count": 0, "failure_count": 0, "warning_count": 0, "evaluator_error_count": 0}, "workflows": [], "failures": [], "warnings": [], "evaluator_errors": []}
        failures: list[str] = []
        warnings: list[str] = []
    else:
        workflow_files = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
        report, failures, warnings = build_report(workflow_files, tier=tier, policy=policy, output_path=args.output or "")
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for warning in warnings:
            print(warning)
        for failure in failures:
            print(failure)
        if failures:
            print(f"\ncost-guard[{tier}]: {len(failures)} failure(s) found.")
        else:
            print(f"cost-guard[{tier}]: all {report['summary']['workflow_count']} workflow(s) passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
