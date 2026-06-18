#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys

BRANCH_LEGACY = re.compile(
    r'^(feat|fix|docs|chore|test|refactor|governance)/mp-cat-\d{3}-bead-cat-\d{3}-\d{3}-[a-z0-9-]+$'
)
BRANCH_NEW = re.compile(
    r'^(feat|fix|docs|chore|test|refactor|governance)/'
    r'mp-cat-[sabc]\d{3}-\dc\d{2}-bead-cat-[sabc]\d{3}-\dc\d{2}-\d{2}-[a-z0-9-]+$'
)


def build(kind: str, mission: str, bead: str, slug: str) -> str:
    mission_l = mission.lower()
    bead_l = bead.lower()
    slug_l = re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-') or 'work'
    return f'{kind}/{mission_l}-{bead_l}-{slug_l}'


def validate(branch: str) -> bool:
    return bool(BRANCH_NEW.match(branch or '') or BRANCH_LEGACY.match(branch or ''))


def main() -> int:
    ap = argparse.ArgumentParser(description='Build or validate CAT GitHub branch names.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    build_cmd = sub.add_parser('build')
    build_cmd.add_argument('--type', default='feat', choices=[
        'feat', 'fix', 'docs', 'chore', 'test', 'refactor', 'governance',
    ])
    build_cmd.add_argument('--mission', required=True)
    build_cmd.add_argument('--bead', required=True)
    build_cmd.add_argument('--slug', required=True)
    validate_cmd = sub.add_parser('validate')
    validate_cmd.add_argument('branch')
    args = ap.parse_args()

    if args.cmd == 'build':
        print(build(args.type, args.mission, args.bead, args.slug))
        return 0
    ok = validate(args.branch)
    print(f'Branch valid: {ok}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
