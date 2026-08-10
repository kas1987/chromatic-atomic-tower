#!/usr/bin/env python3
"""Read-only GitHub branch-protection audit for CAT promotion policy."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_CHECKS = ['validate', 'cat-ci', 'CAT Governance CI', 'LOGHOUSE CI']


def evaluate_protection(data: dict[str, Any], required_checks: list[str] | None = None) -> dict[str, Any]:
    required_checks = required_checks or DEFAULT_REQUIRED_CHECKS
    checks = ((data.get('required_status_checks') or {}).get('contexts') or [])
    reviews = data.get('required_pull_request_reviews') or {}
    result = {
        'required_checks': checks,
        'missing_required_checks': [check for check in required_checks if check not in checks],
        'required_approving_review_count': int(reviews.get('required_approving_review_count') or 0),
        'conversation_resolution': bool((data.get('required_conversation_resolution') or {}).get('enabled')),
        'admins_enforced': bool((data.get('enforce_admins') or {}).get('enabled')),
        'force_pushes_allowed': bool((data.get('allow_force_pushes') or {}).get('enabled')),
        'deletions_allowed': bool((data.get('allow_deletions') or {}).get('enabled')),
    }
    result['compliant'] = not result['missing_required_checks'] and all([
        result['required_approving_review_count'] >= 1,
        result['conversation_resolution'],
        result['admins_enforced'],
        not result['force_pushes_allowed'],
        not result['deletions_allowed'],
    ])
    return result


def fetch_protection(repo: str, branch: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        result = subprocess.run(
            ['gh', 'api', f'repos/{repo}/branches/{branch}/protection'],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f'GitHub protection read failed: {exc}'
    if result.returncode != 0:
        return None, f'GitHub protection read failed with exit {result.returncode}'
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f'GitHub protection response was invalid JSON: {exc}'


def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only CAT branch-protection audit.')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', default='master')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data, error = fetch_protection(args.repo, args.branch)
    report: dict[str, Any] = {
        'schema_version': '1.0.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'repository': args.repo,
        'branch': args.branch,
        'read_only': True,
        'required_checks_policy': DEFAULT_REQUIRED_CHECKS,
        'error': error,
    }
    if data is not None:
        report['evaluation'] = evaluate_protection(data)
    else:
        report['evaluation'] = None
    rendered = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    if error:
        return 2
    return 0 if report['evaluation']['compliant'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
