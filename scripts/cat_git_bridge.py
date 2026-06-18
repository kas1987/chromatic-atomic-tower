#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from cat_changed_files_guard import check as check_changed_files
except ModuleNotFoundError:
    from scripts.cat_changed_files_guard import check as check_changed_files

PR_TITLE_LEGACY = re.compile(r'^\[(MP-CAT-\d{3})\]\[(BEAD-CAT-\d{3}-\d{3})\] .+')
PR_TITLE_NEW = re.compile(
    r'^\[(MP-CAT-[SABC]\d{3}-\dC\d{2})\]\[(BEAD-CAT-[SABC]\d{3}-\dC\d{2}-\d{2})\] .+'
)
BRANCH_LEGACY = re.compile(
    r'^(feat|fix|docs|chore|test|refactor|governance)/mp-cat-(\d{3})-bead-cat-(\d{3})-(\d{3})-[a-z0-9-]+$'
)
BRANCH_NEW = re.compile(
    r'^(feat|fix|docs|chore|test|refactor|governance)/'
    r'mp-cat-([sabc]\d{3}-\dc\d{2})-bead-cat-(\2-\d{2})-[a-z0-9-]+$'
)


def _format_new_mission(stem: str) -> str:
    tier, cx = stem.split('-', 1)
    return f'MP-CAT-{tier.upper()}-{cx.upper()}'


def _format_new_bead(stem: str) -> str:
    body, seq = stem.rsplit('-', 1)
    tier, cx = body.split('-', 1)
    return f'BEAD-CAT-{tier.upper()}-{cx.upper()}-{seq}'


def check_title(title: str):
    for pattern in (PR_TITLE_NEW, PR_TITLE_LEGACY):
        match = pattern.match(title or '')
        if match:
            return True, match.group(1), match.group(2), ''
    return False, None, None, (
        'PR title must match [MP-CAT-###][BEAD-CAT-###-###] Title or '
        '[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Title'
    )


def check_branch(branch: str):
    match = BRANCH_NEW.match(branch or '')
    if match:
        return True, _format_new_mission(match.group(2)), _format_new_bead(match.group(3)), ''
    match = BRANCH_LEGACY.match(branch or '')
    if match:
        mission = f'MP-CAT-{match.group(2)}'
        bead = f'BEAD-CAT-{match.group(3)}-{match.group(4)}'
        return True, mission, bead, ''
    return False, None, None, (
        'Branch must match type/mp-cat-###-bead-cat-###-###-slug or '
        'type/mp-cat-a010-4c01-bead-cat-a010-4c01-01-slug'
    )


def check_commit(commit_message: str, mission_id: str, bead_id: str):
    msg = commit_message or ''
    ok = f'[{mission_id}]' in msg and f'[{bead_id}]' in msg
    return ok, '' if ok else 'Commit message must include [MP-CAT-...] and [BEAD-CAT-...] tokens'


def validate_pr(
    title: str,
    branch: str,
    commit_message: str,
    bead_path: str,
    changed_files_path: str | None = None,
    write_report: bool = False,
):
    checks: list[dict] = []
    errors: list[str] = []

    ok_t, m_t, b_t, err = check_title(title)
    checks.append({'check': 'pr_title', 'passed': ok_t})
    if err:
        errors.append(err)

    ok_b, m_b, b_b, err = check_branch(branch)
    checks.append({'check': 'branch', 'passed': ok_b})
    if err:
        errors.append(err)

    mission_id = m_t or m_b or 'UNKNOWN'
    bead_id = b_t or b_b or 'UNKNOWN'

    if m_t and m_b and m_t != m_b:
        errors.append(f'Mission ID mismatch between PR title ({m_t}) and branch ({m_b})')
    if b_t and b_b and b_t != b_b:
        errors.append(f'BEAD ID mismatch between PR title ({b_t}) and branch ({b_b})')

    ok_c, err = check_commit(commit_message, mission_id, bead_id)
    checks.append({'check': 'commit_message', 'passed': ok_c})
    if err:
        errors.append(err)

    changed_files: list[str] = []
    if changed_files_path:
        scope = check_changed_files(bead_path, changed_files_path)
        checks.append({'check': 'changed_files_scope', 'passed': scope['allowed']})
        errors.extend(scope['errors'])
        changed_files = scope['changed_files']

    status = 'passed' if not errors else 'failed'
    report = {
        'status': status,
        'mission_id': mission_id,
        'bead_id': bead_id,
        'checks': checks,
        'errors': errors,
        'changed_files': changed_files,
    }
    if write_report:
        out = Path('evidence/github/reports')
        out.mkdir(parents=True, exist_ok=True)
        (out / 'github_bridge_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        (out / 'github_bridge_report.md').write_text(
            '# GitHub Bridge Report\n\n```json\n' + json.dumps(report, indent=2) + '\n```\n',
            encoding='utf-8',
        )
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description='CAT GitHub Bridge validator.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    validate_cmd = sub.add_parser('validate-pr')
    validate_cmd.add_argument('--title', required=True)
    validate_cmd.add_argument('--branch', required=True)
    validate_cmd.add_argument('--commit-message', required=True)
    validate_cmd.add_argument('--bead', required=True)
    validate_cmd.add_argument('--changed-files')
    validate_cmd.add_argument('--write-report', action='store_true')
    args = ap.parse_args()

    if args.cmd == 'validate-pr':
        report = validate_pr(
            args.title,
            args.branch,
            args.commit_message,
            args.bead,
            args.changed_files,
            args.write_report,
        )
        print(f"GitHub Bridge status: {report['status']}")
        for error in report['errors']:
            print(f'ERROR: {error}')
        return 0 if report['status'] == 'passed' else 1
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
