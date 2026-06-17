#!/usr/bin/env python3
"""Run strict CAT root hygiene: optional cleanup + validation + report."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT, rel

TRANSIENT_ROOT_PATTERNS = (
    'pytest-cache-files-*',
)


def remove_transient_root_artifacts(root: Path = ROOT) -> list[Path]:
    removed: list[Path] = []
    for pattern in TRANSIENT_ROOT_PATTERNS:
        for path in sorted(root.glob(pattern), key=lambda p: p.name.lower()):
            if not path.exists():
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(path)
    return removed


def run_cmd(args: list[str], root: Path = ROOT) -> int:
    proc = subprocess.run(args, cwd=str(root))
    return int(proc.returncode)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Clean known transient root artifacts, validate CAT contracts, and emit hygiene report.'
    )
    parser.add_argument(
        '--no-clean',
        action='store_true',
        help='Skip transient root artifact cleanup before validation.',
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip branch hygiene report generation step.',
    )
    parser.add_argument(
        '--mode',
        choices=['enforce', 'warn', 'off'],
        default=(os.environ.get('CAT_ROOT_HYGIENE_MODE', 'enforce').strip().lower() or 'enforce'),
        help='Root hygiene enforcement mode passed to cat_validate.py.',
    )
    parser.add_argument(
        '--kill-switch',
        action='store_true',
        default=os.environ.get('CAT_HYGIENE_KILL_SWITCH', '0').strip().lower() in {'1', 'true', 'yes', 'on'},
        help='Disable all hygiene enforcement checks for this run.',
    )

    args, unknown = parser.parse_known_args(argv)
    non_placeholder = [item for item in unknown if item.strip() and item.strip() != '.']
    if non_placeholder:
        parser.error(f'unrecognized arguments: {" ".join(non_placeholder)}')
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mode = 'off' if args.kill_switch else args.mode

    if args.kill_switch:
        print('Hygiene kill switch enabled: all hygiene enforcement set to off for this run.')

    if not args.no_clean:
        removed = remove_transient_root_artifacts(ROOT)
        if removed:
            print('Removed transient root artifacts:')
            for item in removed:
                print(f'  - {rel(item)}')
        else:
            print('No transient root artifacts found.')

    print(f'Running CAT validation (--all, root hygiene mode={mode})...')
    validate_rc = run_cmd(
        [sys.executable, 'scripts/cat_validate.py', '--all', '--root-hygiene-mode', mode],
        ROOT,
    )

    report_rc = 0
    if not args.no_report:
        print('Running root hygiene report...')
        report_rc = run_cmd(
            [sys.executable, 'scripts/cat_branch_hygiene.py', '--write-report'],
            ROOT,
        )

    # In non-enforcing modes, report generation stays informational.
    if mode != 'enforce':
        report_rc = 0

    if validate_rc == 0 and report_rc == 0:
        print('Strict CAT hygiene validation PASSED.')
        return 0

    print('Strict CAT hygiene validation FAILED.')
    return validate_rc or report_rc


if __name__ == '__main__':
    raise SystemExit(main())
