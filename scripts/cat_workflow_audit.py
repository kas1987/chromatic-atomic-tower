#!/usr/bin/env python3
"""Inventory local and optional GitHub-managed workflow provenance."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() or 'unknown'


def local_inventory(root: Path) -> list[dict[str, Any]]:
    workflows = []
    for path in sorted(list((root / '.github' / 'workflows').glob('*.yml')) + list((root / '.github' / 'workflows').glob('*.yaml'))):
        raw = path.read_text(encoding='utf-8')
        data = yaml.safe_load(raw) or {}
        triggers = data.get(True, data.get('on', {}))
        jobs = data.get('jobs', {}) or {}
        workflows.append({
            'name': data.get('name', path.stem),
            'path': str(path.relative_to(root)).replace('\\', '/'),
            'source_sha': _git(root, 'hash-object', str(path.relative_to(root))),
            'triggers': sorted(triggers) if isinstance(triggers, dict) else triggers,
            'permissions_declared': 'permissions' in data or all(isinstance(job, dict) and 'permissions' in job for job in jobs.values()),
            'concurrency_declared': 'concurrency' in data or all(isinstance(job, dict) and 'concurrency' in job for job in jobs.values()),
            'timeout_jobs': sorted(name for name, job in jobs.items() if isinstance(job, dict) and 'timeout-minutes' in job),
            'job_count': len(jobs),
        })
    return workflows


def live_inventory(root: Path) -> tuple[list[dict[str, Any]], str | None]:
    try:
        result = subprocess.run(
            ['gh', 'workflow', 'list', '--json', 'name,path,state'],
            cwd=root, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f'GitHub workflow inventory unavailable: {exc}'
    if result.returncode != 0:
        return [], f'GitHub workflow inventory failed with exit {result.returncode}'
    try:
        data = json.loads(result.stdout or '[]')
    except json.JSONDecodeError as exc:
        return [], f'GitHub workflow inventory returned invalid JSON: {exc}'
    safe = []
    for item in data:
        safe.append({key: item.get(key) for key in ('name', 'path', 'state')})
    return safe, None


def build_report(root: Path, *, include_live: bool = True) -> dict[str, Any]:
    local = local_inventory(root)
    live, live_error = live_inventory(root) if include_live else ([], 'live inventory skipped by operator')
    local_paths = {item['path'] for item in local}
    gaps = [item for item in live if item.get('path') not in local_paths]
    return {
        'schema_version': '1.0.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'head_sha': _git(root, 'rev-parse', 'HEAD'),
        'default_branch': _git(root, 'symbolic-ref', 'refs/remotes/origin/HEAD').removeprefix('refs/remotes/origin/'),
        'local_workflows': local,
        'live_workflows': live,
        'provenance_gaps': gaps,
        'live_inventory_error': live_error,
        'summary': {
            'local_count': len(local),
            'live_count': len(live),
            'provenance_gap_count': len(gaps),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Inventory local and GitHub workflow provenance.')
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--skip-live', action='store_true')
    args = parser.parse_args()
    report = build_report(args.root.resolve(), include_live=not args.skip_live)
    rendered = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
