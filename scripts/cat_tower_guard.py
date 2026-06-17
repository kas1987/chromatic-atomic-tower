#!/usr/bin/env python3
"""cat_tower_guard.py - unified Tower state freshness + hygiene guard."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from cat_branch_hygiene import check_hygiene
from cat_state_freshness import check_freshness
from common import ROOT, rel, validate_with_schema


def run_tower_guard(
    root: Path = ROOT,
    allowlist_path: Path | None = None,
    branch_name: str | None = None,
) -> dict:
    freshness = check_freshness(root)
    hygiene = check_hygiene(root=root, allowlist_path=allowlist_path, branch_name=branch_name)

    checks = [
        {
            "name": "state_freshness",
            "status": "pass" if freshness.is_fresh else "fail",
            "ok": freshness.ok,
            "issues": freshness.drift,
        },
        {
            "name": "branch_root_hygiene",
            "status": "pass" if hygiene.passed else "fail",
            "ok": hygiene.ok,
            "issues": hygiene.issues,
        },
    ]

    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"

    return {
        "version": "0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "status": status,
        "checks": checks,
    }


def validate_report(report: dict, schema_path: Path) -> list[str]:
    return validate_with_schema(report, schema_path)


def render_markdown(report: dict) -> str:
    lines = ["# Tower Guard Report", "", f"Overall status: {report['status']}", ""]
    for check in report.get("checks", []):
        lines.append(f"## {check['name']}")
        lines.append("")
        lines.append(f"Status: {check['status']}")
        lines.append("")
        if check.get("ok"):
            lines.append("### OK")
            for item in check["ok"]:
                lines.append(f"- {item}")
            lines.append("")
        if check.get("issues"):
            lines.append("### Issues")
            for item in check["issues"]:
                lines.append(f"- {item}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(report: dict, report_path: Path, json_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CAT unified Tower guard checks.")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write Markdown and JSON reports under evidence/tower/",
    )
    args = parser.parse_args()

    report = run_tower_guard()
    schema_path = ROOT / "schemas/tower_guard_report.schema.json"
    schema_errors = validate_report(report, schema_path)

    print(f"Tower guard status: {report['status']}")
    for check in report["checks"]:
        print(f"- {check['name']}: {check['status']}")

    if schema_errors:
        print("Schema validation failed:")
        for error in schema_errors:
            print(f"  - {error}")

    if args.write_report:
        report_path = ROOT / "evidence/tower/tower_guard_report.md"
        json_path = ROOT / "evidence/tower/tower_guard_report.json"
        write_reports(report, report_path, json_path)
        print(f"Markdown report written: {rel(report_path)}")
        print(f"JSON report written: {rel(json_path)}")

    return 0 if report["status"] == "pass" and not schema_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
