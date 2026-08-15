#!/usr/bin/env python3
"""Initialize CAT's local official Beads database without touching agent policy."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from cat_beads import ROOT, resolve_bd_command

MINIMUM_VERSION = (1, 0, 0)
DEFAULT_REMOTE = 'git+ssh://git@github.com/kas1987/chromatic-atomic-tower.git'


def _version(text: str) -> tuple[int, int, int]:
    match = re.search(r'bd version (\d+)\.(\d+)\.(\d+)', text)
    return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)


def _run(command: list[str], args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command + args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def main() -> int:
    parser = argparse.ArgumentParser(description='Initialize CAT official Beads/Dolt state.')
    parser.add_argument('--remote', default=DEFAULT_REMOTE)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    try:
        command = resolve_bd_command()
    except Exception as exc:
        print(f'CAT Beads initialization blocked: {exc}')
        return 1
    env = os.environ.copy()
    env['BEADS_DIR'] = str((ROOT / '.beads').resolve())
    version_result = _run(command, ['--version'], env)
    version = _version(f'{version_result.stdout}\n{version_result.stderr}')
    print(f'bd version: {version_result.stdout.strip()}')
    if version < MINIMUM_VERSION:
        print(f'CAT requires bd >= {".".join(map(str, MINIMUM_VERSION))}')
        return 1
    if not args.verify_only and not (ROOT / '.beads').exists():
        initialized = _run(command, ['init', '--non-interactive', '--skip-agents', '--skip-hooks', '-p', 'cat'], env)
        if initialized.returncode != 0:
            print(initialized.stderr or initialized.stdout)
            return initialized.returncode
    if not (ROOT / '.beads').exists():
        print('CAT Beads database is not initialized; run without --verify-only.')
        return 1
    _run(command, ['dolt', 'remote', 'remove', 'origin'], env)
    remote = _run(command, ['dolt', 'remote', 'add', 'origin', args.remote], env)
    if remote.returncode != 0 and 'already exists' not in (remote.stderr or '').lower():
        print(remote.stderr or remote.stdout)
        return remote.returncode
    print(f'CAT official Beads ready; remote origin={args.remote}')
    print('AGENTS.md was not modified by initialization.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
