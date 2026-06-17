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

# --- Root allowlist (keep in sync with CAT_MANIFEST.md sections 3, 3.1, 3.2, 4) ---

# Required root files (CAT_MANIFEST.md section 3) + optional root files (section 3.1).
ALLOWED_ROOT_FILES = {
    # section 3 — required
    'README.md', 'START_HERE.md', 'PDR_CAT_000_ESTABLISH_CORE_REPO.md',
    'CAT_MANIFEST.md', 'CAT_PRINCIPLES.md', 'CHROMATIC_TREES.md', 'AGENTS.md',
    'requirements.txt', 'Makefile',
    # section 3.1 — allowed optional
    'CAT_ROADMAP.md', 'CHANGELOG.md', 'GOVERNANCE.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'QUICKSTART.md', 'VERSION', 'CHROMATIC_TREES.worktree.json',
    'pyproject.toml', '.editorconfig', '.env.example', '.gitignore',
}

# Canonical directories (section 4) + allowed tooling directories (section 3.2).
ALLOWED_ROOT_DIRS = set(REQUIRED_DIRS) | {
    '.github', '.vscode', '.agent', 'tests',
}

# Transient / VCS / cache entries that are gitignored and not governed by the manifest.
IGNORED_ROOT_ENTRIES = {
    '.git', '.venv', '__pycache__', '.pytest_cache', '.claude', '.DS_Store',
    '.github_app_token_cache',
}


def find_stray_root_entries() -> list[str]:
    """Flag any root entry not blessed by the manifest allowlists."""
    stray: list[str] = []
    for entry in sorted(p.name for p in ROOT.iterdir()):
        if entry in IGNORED_ROOT_ENTRIES:
            continue
        target = ROOT / entry
        if target.is_dir():
            if entry not in ALLOWED_ROOT_DIRS:
                stray.append(entry + '/')
        else:
            if entry not in ALLOWED_ROOT_FILES:
                stray.append(entry)
    return stray


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
        print('CAT repo check failed.')
        if missing:
            print('Missing required files/directories:')
            for item in missing:
                print(f'  - {item}')
        if stray:
            print('Stray root entries not blessed by CAT_MANIFEST.md (sections 3, 3.1, 3.2, 4):')
            for item in stray:
                print(f'  - {item}')
            print('Fix: move it under the right plane, gitignore it, or add it to the manifest + this allowlist.')
        return 1

    print('CAT repo check passed.')
    print(f'Required files checked: {len(REQUIRED_FILES)}')
    print(f'Required directories checked: {len(REQUIRED_DIRS)}')
    print('No stray root entries.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
