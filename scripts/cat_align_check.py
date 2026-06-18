#!/usr/bin/env python3
"""cat_align_check.py — unified mission/BEAD alignment check for CI and GO gate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from cat_state_freshness import check_alignment
from common import ROOT, rel


def build_report(root: Path = ROOT) -> dict:
    result = check_alignment(root)
    return {
        'version': '0.1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'status': 'pass' if result.is_aligned else 'fail',
        'drift_count': len(result.drift),
        'ok': result.ok,
        'drift': [
            {
                'code': item.code,
                'message': item.message,
                'remediation': item.remediation,
            }
            for item in result.drift
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [
        '# Alignment Check Report',
        '',
        f"Status: **{report['status']}**",
        f"Generated: {report['generated_at']}",
        '',
    ]
    if report.get('ok'):
        lines.append('## OK')
        for item in report['ok']:
            lines.append(f'- {item}')
        lines.append('')
    if report.get('drift'):
        lines.append('## Drift')
        for item in report['drift']:
            lines.append(f"- **[{item['code']}]** {item['message']}")
            if item.get('remediation'):
                lines.append(f"  - Remediation: {item['remediation']}")
        lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Run mission/BEAD alignment check.')
    parser.add_argument('--strict', action='store_true', help='Exit 1 on any drift.')
    parser.add_argument('--write-report', action='store_true', help='Write evidence/tower/align_check_report.json')
    parser.add_argument('--json', action='store_true', help='Print JSON report to stdout.')
    args = parser.parse_args()

    report = build_report()
    print(render_markdown(report))

    if args.json:
        print(json.dumps(report, indent=2))

    if args.write_report:
        json_path = ROOT / 'evidence/tower/align_check_report.json'
        md_path = ROOT / 'evidence/tower/align_check_report.md'
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        md_path.write_text(render_markdown(report), encoding='utf-8')
        print(f'JSON report: {rel(json_path)}')
        print(f'Markdown report: {rel(md_path)}')

    if args.strict and report['status'] != 'pass':
        return 1
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
