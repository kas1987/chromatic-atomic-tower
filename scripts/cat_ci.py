#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
try:
    from common import ROOT, validate_with_schema
except ModuleNotFoundError:
    from scripts.common import ROOT, validate_with_schema

CHECKS = [
    ('repo_structure', ['python', 'scripts/cat_check_repo.py']),
    ('schema_validation', ['python', 'scripts/cat_validate.py', '--all']),
    ('alignment_check', ['python', 'scripts/cat_align_check.py', '--strict']),
    ('tower_status', ['python', 'scripts/cat_status.py']),
]

def run_check(check_id: str, command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    details = (proc.stdout + proc.stderr).strip()
    return {'id': check_id, 'status': 'passed' if proc.returncode == 0 else 'failed', 'command': ' '.join(command), 'returncode': proc.returncode, 'details': details[-4000:]}

def build_report(mode: str, include_pytest: bool = False) -> dict:
    checks = [run_check(check_id, command) for check_id, command in CHECKS]
    if include_pytest:
        checks.append(run_check('tests', ['pytest', '-q']))
    passed = sum(1 for c in checks if c['status'] == 'passed')
    failed = sum(1 for c in checks if c['status'] == 'failed')
    skipped = sum(1 for c in checks if c['status'] == 'skipped')
    return {
        'report_id': 'CAT-CI-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'mode': mode,
        'status': 'failed' if failed else 'passed',
        'checks': checks,
        'summary': {'passed': passed, 'failed': failed, 'skipped': skipped},
    }

def write_report(report: dict) -> None:
    report_dir = ROOT / 'evidence/ci/reports'
    summary_dir = ROOT / 'evidence/ci/summaries'
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / 'cat_ci_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# CAT CI Report', '', f"Report ID: {report['report_id']}", f"Status: {report['status']}", '', '## Summary', f"- Passed: {report['summary']['passed']}", f"- Failed: {report['summary']['failed']}", f"- Skipped: {report['summary']['skipped']}", '', '## Checks']
    for check in report['checks']:
        lines.append(f"- {check['id']}: {check['status']} (`{check.get('command','')}`)")
    (report_dir / 'cat_ci_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

def main() -> int:
    parser = argparse.ArgumentParser(description='Run CAT CI governance checks locally.')
    parser.add_argument('--mode', default='local')
    parser.add_argument('--write-report', action='store_true')
    parser.add_argument('--include-pytest', action='store_true', help='Also run pytest. Avoid using this from pytest tests.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    report = build_report(args.mode, include_pytest=args.include_pytest)
    errors = validate_with_schema(report, ROOT / 'schemas/ci_report.schema.json')
    if errors:
        for error in errors: print(error)
        return 1
    if args.write_report:
        write_report(report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"CAT CI status: {report['status']}")
        for check in report['checks']:
            print(f"{check['status'].upper()} {check['id']}")
    return 0 if report['status'] == 'passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
