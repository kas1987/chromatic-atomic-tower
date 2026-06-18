#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import yaml


def load_lines(path: str | Path) -> list[str]:
    return [
        line.strip()
        for line in Path(path).read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch('/' + path, pattern)
        for pattern in patterns
    )


def check(bead_path: str | Path, changed_files_path: str | Path) -> dict:
    bead = yaml.safe_load(Path(bead_path).read_text(encoding='utf-8'))
    allowed = bead.get('allowed_paths', [])
    forbidden = bead.get('forbidden_paths', [])
    changed = load_lines(changed_files_path)
    errors: list[str] = []
    for path in changed:
        if matches_any(path, forbidden):
            errors.append(f'Forbidden path changed: {path}')
        elif not matches_any(path, allowed):
            errors.append(f'Changed file outside BEAD allowed paths: {path}')
    return {
        'allowed': not errors,
        'errors': errors,
        'changed_files': changed,
        'bead_id': bead.get('bead_id'),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='Validate changed files against a BEAD allowed_paths contract.')
    ap.add_argument('--bead', required=True)
    ap.add_argument('--changed-files', required=True)
    args = ap.parse_args()
    result = check(args.bead, args.changed_files)
    print(f"Changed-file scope allowed: {result['allowed']}")
    for error in result['errors']:
        print(f'ERROR: {error}')
    return 0 if result['allowed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
