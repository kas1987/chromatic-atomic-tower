#!/usr/bin/env python3
"""Check or explicitly install CAT's versioned Git hook contract."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def install_hook(source: Path, target: Path, *, apply: bool = False) -> str:
    if not source.exists():
        raise FileNotFoundError(f"hook source not found: {source}")
    if not apply:
        return f"DRY-RUN: would install {source} -> {target}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    if os.name != 'nt':
        target.chmod(target.stat().st_mode | 0o111)
    return f"INSTALLED: {source} -> {target}"


def main() -> int:
    parser = argparse.ArgumentParser(description='Install the versioned CAT pre-push hook.')
    parser.add_argument('--root', type=Path, default=Path('.'), help='Repository root')
    parser.add_argument('--install', action='store_true', help='Write the hook into the selected root')
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / 'scripts' / 'hooks' / 'pre-push.sh'
    target = root / '.git' / 'hooks' / 'pre-push'
    print(install_hook(source, target, apply=args.install))
    if not args.install:
        print('Use --install only after reviewing the source and target.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
