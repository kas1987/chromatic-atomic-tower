#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    'README.md',
    'START_HERE.md',
    'PDR_CAT_000_ESTABLISH_CORE_REPO.md',
    'CAT_MANIFEST.md',
    'CAT_PRINCIPLES.md',
    'CAT_ROADMAP.md',
    'docs/operations/SPRINT_000_PLAN.md',
    'QUICKSTART.md',
    'AGENTS.md',
    'CHROMATIC_TREES.md',
    'missions/registry/MISSION_REGISTRY.yaml',
    'missions/active/MP-CAT-000_ESTABLISH_CORE.yaml',
    'beads/active/BEAD-CAT-000-001.yaml',
    'agents/registry/AGENT_REGISTRY.yaml',
    'gates/confidence/CONFIDENCE_GATE.md',
    'schemas/mission.schema.json',
    'schemas/bead.schema.json',
    'scripts/cat_validate.py',
    'scripts/cat_resolve_go.py',
]

REQUIRED_DIRS = [
    'missions', 'beads', 'agents', 'gates', 'evidence', 'schemas', 'scripts',
    'playbooks', 'docs', 'state', 'learnings', 'prompts', 'checklists', 'reference'
]


def main() -> int:
    missing: list[str] = []
    for item in REQUIRED_FILES:
        if not (ROOT / item).is_file():
            missing.append(item)
    for item in REQUIRED_DIRS:
        if not (ROOT / item).is_dir():
            missing.append(item + '/')

    if missing:
        print('CAT repo check failed. Missing:')
        for item in missing:
            print(f'  - {item}')
        return 1

    print('CAT repo check passed.')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Required directories checked: {len(REQUIRED_DIRS)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
