#!/usr/bin/env python3
"""Root hygiene validation script with configurable enforcement mode.

--mode enforce  (default) exits 1 when stray root entries are found
--mode warn     prints issues but exits 0 (used in builder CI contexts)
--mode off      skips all checks and exits 0
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from common import ROOT, load_yaml
from cat_branch_hygiene import find_root_hygiene_issues, load_root_allowlist


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate CAT repository root hygiene.')
    parser.add_argument(
        '--mode',
        choices=['enforce', 'warn', 'off'],
        default=None,
        help='Enforcement mode (default from CAT_ROOT_HYGIENE_MODE or enforce).',
    )
    parser.add_argument('--root', default=None, help='Repository root path (defaults to CAT_ROOT or repo root).')
    args = parser.parse_args()

    mode_raw = args.mode or os.environ.get('CAT_ROOT_HYGIENE_MODE') or 'enforce'
    mode = mode_raw.strip().lower()
    if mode not in {'enforce', 'warn', 'off'}:
        mode = 'enforce'

    if mode == 'off':
        print('SKIP root hygiene: enforcement disabled (mode=off)')
        return 0

    root = Path(args.root).resolve() if args.root else ROOT
    allowlist_path = root / 'gates/hygiene/root_allowlist.yaml'

    if not allowlist_path.exists():
        msg = f'root allowlist missing: {allowlist_path.relative_to(root)}'
        if mode == 'warn':
            print(f'WARN root hygiene: {msg}')
            return 0
        print(f'FAIL root hygiene: {msg}')
        return 1

    allowlist = load_root_allowlist(allowlist_path)
    issues = find_root_hygiene_issues(root, allowlist)

    if not issues:
        print('PASS root hygiene: root entries satisfy allowlist')
        return 0

    if mode == 'warn':
        print('WARN root hygiene: root contains non-allowlisted entries (non-blocking)')
        for issue in issues:
            print(f'  - {issue}')
        return 0

    print('FAIL root hygiene: root contains non-allowlisted entries')
    for issue in issues:
        print(f'  - {issue}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
