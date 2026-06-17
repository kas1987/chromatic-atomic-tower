#!/usr/bin/env python3
"""cat_branch_hygiene.py - dry-run branch and root artifact hygiene checks."""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from common import ROOT, load_yaml, rel


@dataclass
class HygieneResult:
    issues: list[str] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues

    def report(self) -> str:
        lines: list[str] = []
        for item in self.ok:
            lines.append(f"OK    {item}")
        for item in self.issues:
            lines.append(f"ISSUE {item}")
        if self.passed:
            lines.append("Branch hygiene PASS - no blocking issues detected.")
        else:
            lines.append(f"Branch hygiene FAIL - {len(self.issues)} issue(s) detected.")
        return "\n".join(lines)


def load_root_allowlist(path: Path) -> dict[str, set[str]]:
    data = load_yaml(path) or {}
    allowed_files = set(data.get("allowed_files", []))
    allowed_dirs = set(data.get("allowed_dirs", []))
    ignored_entries = set(data.get("ignored_entries", []))
    return {
        "allowed_files": allowed_files,
        "allowed_dirs": allowed_dirs,
        "ignored_entries": ignored_entries,
    }


def find_root_hygiene_issues(root: Path, allowlist: dict[str, set[str]]) -> list[str]:
    issues: list[str] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        name = entry.name
        if any(fnmatch.fnmatch(name, pattern) for pattern in allowlist["ignored_entries"]):
            continue
        if entry.is_file() and name not in allowlist["allowed_files"]:
            issues.append(f"stray root file: {name}")
        elif entry.is_dir() and name not in allowlist["allowed_dirs"]:
            issues.append(f"stray root directory: {name}")
    return issues


def evaluate_branch_hygiene(branch_name: str) -> list[str]:
    issues: list[str] = []
    name = (branch_name or "").strip()
    lowered = name.lower()
    if not name or lowered == "head":
        issues.append("detached HEAD is not allowed for GO execution")
    if lowered in {"main", "master"}:
        issues.append(f"branch '{name}' is protected; use a topic branch")
    return issues


def detect_branch_name(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def check_hygiene(
    root: Path = ROOT,
    allowlist_path: Path | None = None,
    branch_name: str | None = None,
) -> HygieneResult:
    result = HygieneResult()

    if allowlist_path is None:
        allowlist_path = root / "gates/hygiene/root_allowlist.yaml"

    if not allowlist_path.exists():
        result.issues.append(f"root allowlist missing: {rel(allowlist_path)}")
        return result

    allowlist = load_root_allowlist(allowlist_path)

    active_branch = branch_name if branch_name is not None else detect_branch_name(root)
    branch_issues = evaluate_branch_hygiene(active_branch)
    if branch_issues:
        result.issues.extend(branch_issues)
    else:
        result.ok.append(f"branch is hygienic: {active_branch}")

    root_issues = find_root_hygiene_issues(root, allowlist)
    if root_issues:
        result.issues.extend(root_issues)
    else:
        result.ok.append("root entries satisfy hygiene allowlist")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run dry-run branch/root hygiene checks for CAT Tower governance."
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write report to evidence/tower/branch_hygiene_report.md",
    )
    args = parser.parse_args()

    result = check_hygiene()
    report_text = result.report()
    print(report_text)

    if args.write_report:
        report_path = ROOT / "evidence/tower/branch_hygiene_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f"# Branch Hygiene Report\n\n```\n{report_text}\n```\n",
            encoding="utf-8",
        )
        print(f"\nReport written: {rel(report_path)}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
