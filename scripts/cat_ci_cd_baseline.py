#!/usr/bin/env python3
"""Compare the pre-remediation cost baseline with current tier outcomes."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.cat_cost_guard import build_report, load_policy, _git_value
except ModuleNotFoundError:
    from cat_cost_guard import build_report, load_policy, _git_value


def collect(root: Path, previous: Path) -> dict[str, Any]:
    prior = json.loads(previous.read_text(encoding='utf-8'))
    prior_text = str((prior.get('evidence') or {}).get('strict_cost_guard', ''))
    match = re.search(r'(\d+)\s+warnings?', prior_text)
    if not match:
        raise ValueError(f'prior audit does not contain a numeric strict warning baseline: {previous}')
    policy = load_policy(root / 'gates/ci/COST_GUARD_POLICY.yaml')
    workflows = root / '.github' / 'workflows'
    workflow_files = sorted(list(workflows.glob('*.yml')) + list(workflows.glob('*.yaml')))
    current: dict[str, Any] = {}
    for tier in ('none', 'balanced', 'strict'):
        report, failures, warnings = build_report(workflow_files, tier=tier, policy=policy)
        current[tier] = {
            'policy_version': report['policy_version'],
            'head_sha': report['head_sha'],
            'workflow_count': report['summary']['workflow_count'],
            'failure_count': len(failures),
            'warning_count': len(warnings),
            'exit_code': 1 if failures else 0,
        }
    return {
        'schema_version': '1.0.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'repository': prior.get('repository', 'unknown'),
        'head_sha': _git_value('rev-parse', 'HEAD'),
        'default_branch': _git_value('symbolic-ref', 'refs/remotes/origin/HEAD').removeprefix('refs/remotes/origin/'),
        'historical_baseline': {
            'source_report': str(previous.relative_to(root)).replace('\\', '/'),
            'source_head_sha': prior.get('head_sha'),
            'strict_warning_count': int(match.group(1)),
        },
        'current_tiers': current,
        'rollout': {
            'default_tier': policy['default_tier'],
            'strict_clean': current['strict']['failure_count'] == 0,
            'remote_branch_protection': 'separate human-gated remediation; see BEAD-06',
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Build CAT CI/CD remediation baseline evidence.')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    previous = (args.previous or root / 'evidence/reports/ci-cd-audit/2026-08-10.json').resolve()
    report = collect(root, previous)
    rendered = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
