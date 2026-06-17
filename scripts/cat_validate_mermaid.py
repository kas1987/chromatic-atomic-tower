#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def validate_doc(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    errors: list[str] = []
    opens = text.count('```mermaid')
    closes = text.count('```')
    if opens == 0:
        errors.append(f'{path}: no Mermaid fences found')
    if closes < opens * 2:
        errors.append(f'{path}: Mermaid fence appears unclosed')
    for idx, line in enumerate(text.splitlines(), start=1):
        if line.startswith('\t'):
            errors.append(f'{path}:{idx}: tab indentation in Mermaid doc')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate Mermaid code fences in CAT docs.')
    parser.add_argument('--root', default='.', help='Repository root')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    docs = list((root / 'docs/architecture').glob('*.md'))
    errors: list[str] = []
    for doc in docs:
        if 'MERMAID' in doc.name or 'HARNESS_ENGINEERING' in doc.name:
            errors.extend(validate_doc(doc))
    if errors:
        print('Mermaid validation failed:')
        for error in errors:
            print(f' - {error}')
        return 1
    print('Mermaid validation passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
