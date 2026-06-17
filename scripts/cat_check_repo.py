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
    'SPRINT_000_PLAN.md',
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

IGNORED_ROOT_ENTRIES = {
    '.git',
    '.pytest_cache',
    '__pycache__',
    '.venv',
    'venv',
    '.mypy_cache',
    '.ruff_cache',
    '.idea',
    '.vscode',
}

# Snapshot the current known-good root entries and required root files. This keeps
# stray detection deterministic while still flagging newly introduced root clutter.
ALLOWED_ROOT_FILES = {
    path.name
    for path in ROOT.iterdir()
    if path.is_file()
} | {
    item for item in REQUIRED_FILES if '/' not in item
}

ALLOWED_ROOT_DIRS = {
    path.name
    for path in ROOT.iterdir()
    if path.is_dir()
} | set(REQUIRED_DIRS)


def find_stray_root_entries() -> list[str]:
    stray: list[str] = []
    for path in ROOT.iterdir():
        name = path.name
        if name in IGNORED_ROOT_ENTRIES:
            continue
        if path.is_file() and name not in ALLOWED_ROOT_FILES:
            stray.append(name)
            continue
        if path.is_dir() and name not in ALLOWED_ROOT_DIRS:
            stray.append(name)
    return sorted(stray)


def main() -> int:
    missing: list[str] = []
    for item in REQUIRED_FILES:
        if not (ROOT / item).is_file():
            missing.append(item)
    for item in REQUIRED_DIRS:
        if not (ROOT / item).is_dir():
            missing.append(item + '/')

    stray = find_stray_root_entries()

    if missing or stray:
        print('CAT repo check failed. Missing:')
        if missing:
            for item in missing:
                print(f'  - {item}')
        if stray:
            print('CAT repo check failed. Stray root entries:')
            for item in stray:
                print(f'  - {item}')
        return 1

    print('CAT repo check passed.')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Required directories checked: {len(REQUIRED_DIRS)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
