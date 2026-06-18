#!/usr/bin/env python3
"""Compare CAT repository state to reconciliation target."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from common import ROOT, load_yaml


def check(target_path: Path, root: Path) -> dict:
    target = load_yaml(target_path)
    registry = load_yaml(root / 'missions/registry/MISSION_REGISTRY.yaml')
    roadmap_path = root / 'CAT_ROADMAP.md'
    roadmap = roadmap_path.read_text(encoding='utf-8') if roadmap_path.exists() else ''
    checks: list[dict] = []
    missing: list[str] = []

    active = registry.get('active_mission_id') or ''
    expected_active = target.get('canonical_active_mission_id')
    if expected_active is not None:
        expected_active = expected_active or ''
    checks.append({
        'name': 'active_mission_matches_target',
        'passed': active == (expected_active if expected_active is not None else active),
        'details': f'{active!r} vs {expected_active!r}',
    })

    missions = {m.get('mission_id'): m.get('status') for m in registry.get('missions', [])}
    for mid, status in (target.get('required_missions') or {}).items():
        passed = missions.get(mid) == status
        checks.append({
            'name': f'mission_{mid}_status',
            'passed': passed,
            'details': f'{missions.get(mid)} vs {status}',
        })
        if mid not in missions:
            missing.append(mid)

    for term in target.get('required_roadmap_terms', []):
        passed = term in roadmap
        checks.append({
            'name': f'roadmap_contains_{term[:32]}',
            'passed': passed,
            'details': term,
        })
        if not passed:
            missing.append(f'roadmap term: {term}')

    status = 'passed' if all(c['passed'] for c in checks) else 'failed'
    return {
        'report_id': 'CAT-RECONCILIATION-A009',
        'generated_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'status': status,
        'active_mission_id': active,
        'next_mission_id': target.get('canonical_next_mission_id'),
        'checks': checks,
        'missing': missing,
        'recommendations': [] if status == 'passed' else [
            'Patch registry, roadmap, or target files until all reconciliation checks pass.',
        ],
    }


def write_reports(report: dict, root: Path) -> None:
    outdir = root / 'evidence/reconciliation'
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'reconciliation_report.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8'
    )
    lines = [
        '# CAT Reconciliation Report',
        '',
        f"Status: **{report['status']}**",
        '',
        f"Active Mission: `{report.get('active_mission_id')}`",
        '',
        '## Checks',
        '',
    ]
    for c in report['checks']:
        mark = 'PASS' if c['passed'] else 'FAIL'
        lines.append(f"- [{mark}] {c['name']} - {c.get('details', '')}")
    if report['missing']:
        lines += ['', '## Missing', ''] + [f'- {m}' for m in report['missing']]
    (outdir / 'reconciliation_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default='docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml')
    ap.add_argument('--write-report', action='store_true')
    args = ap.parse_args()
    root = ROOT
    report = check(root / args.target, root)
    if args.write_report:
        write_reports(report, root)
        print('Reconciliation report written.')
    print(f"Reconciliation status: {report['status']}")
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
