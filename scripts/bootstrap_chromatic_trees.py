#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

BRIDGE = """\n## Agent Bridge\n\nThis repo uses ChromaticTrees. Agents must read `CHROMATIC_TREES.md` and `CAT_MANIFEST.md` before adding new folders or files.\n"""


def main() -> int:
    parser = argparse.ArgumentParser(description='Bootstrap ChromaticTrees bridge files for a repo.')
    parser.add_argument('--path', required=True)
    parser.add_argument('--bridge', action='store_true')
    args = parser.parse_args()

    root = Path(args.path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    chromatic_trees = root / 'CHROMATIC_TREES.md'
    if not chromatic_trees.exists():
        chromatic_trees.write_text('# ChromaticTrees\n\nDefine repo tree rules here.\n', encoding='utf-8')
    if args.bridge:
        for name in ['AGENTS.md', 'CLAUDE.md', '.cursorrules']:
            path = root / name
            if path.exists():
                text = path.read_text(encoding='utf-8')
                if 'ChromaticTrees' not in text:
                    path.write_text(text.rstrip() + '\n' + BRIDGE, encoding='utf-8')
            else:
                path.write_text(BRIDGE.lstrip(), encoding='utf-8')
    print(f'ChromaticTrees bootstrapped at {root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
