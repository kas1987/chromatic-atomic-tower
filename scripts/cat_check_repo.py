#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
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
    'requirements.txt',
    'Makefile',
    'missions/registry/MISSION_REGISTRY.yaml',
    'missions/archived/MP-CAT-000_ESTABLISH_CORE.yaml',
    'beads/examples/BEAD-CAT-EXAMPLE-001.yaml',
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

# Static allowlists — keep in sync with CAT_MANIFEST.md sections 3, 3.1, 3.2, 4.
# Building these dynamically would auto-allow any new root file, defeating the guard.
ALLOWED_ROOT_FILES = {
    # section 3 — required
    'README.md', 'START_HERE.md', 'PDR_CAT_000_ESTABLISH_CORE_REPO.md',
    'CAT_MANIFEST.md', 'CAT_PRINCIPLES.md', 'CHROMATIC_TREES.md', 'AGENTS.md',
    'requirements.txt', 'Makefile',
    # section 3.1 — allowed optional
    'CAT_ROADMAP.md', 'CHANGELOG.md', 'GOVERNANCE.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'QUICKSTART.md', 'VERSION', 'CHROMATIC_TREES.worktree.json',
    'pyproject.toml', '.editorconfig', '.env.example', '.gitignore',
    # sprint plans at root (backward-compat; sprint 000+ ship these here)
    'SPRINT_000_PLAN.md', 'SPRINT_001_PLAN.md', 'SPRINT_002_PLAN.md', 'SPRINT_003_PLAN.md',
    'SPRINT_009_PLAN.md', 'SPRINT_010_PLAN.md', 'SPRINT_011_PLAN.md',
    # PDR design records (one per sprint)
    'PDR_CAT_001_STATE_TRANSITION_ENGINE.md',
    'PDR_CAT_002_EVIDENCE_GATE_CLOSEOUT_ENGINE.md',
    'PDR_CAT_003_CI_GOVERNANCE_SELF_HEALING.md',
    'PDR_CAT_004_V2_ALIGNMENT_GUARDS.md',
    'PDR_CAT_A009_REPO_ALIGNMENT_RECONCILIATION.md',
    'PDR_CAT_A010_GITHUB_BRIDGE_PR_GOVERNANCE.md',
    'PDR_CAT_A011_AGENT_SCORECARD_AUTOMATION.md',
}

ALLOWED_ROOT_DIRS = set(REQUIRED_DIRS) | {
    '.github', '.vscode', '.agent', 'tests', 'ci', '.codex',
}

# Transient / VCS / cache entries that are gitignored and not governed by the manifest.
IGNORED_ROOT_ENTRIES = {
    '.git', '.venv', '__pycache__', '.pytest_cache', '.claude', '.DS_Store',
    '.github_app_token_cache', '.beads',
}

# Gitignored glob patterns for secrets/credentials at the root (keep in sync with
# .gitignore: .env, .env.*, *.pem). Expected in local workflows and never stray.
# Note: .env.example is tracked and lives in ALLOWED_ROOT_FILES, so it passes regardless.
IGNORED_ROOT_PATTERNS = ('.env', '.env.*', '*.pem')


def find_stray_root_entries(root: Path = ROOT) -> list[str]:
    """Flag any root entry not blessed by the manifest allowlists.

    Gitignored caches/secrets (IGNORED_ROOT_ENTRIES + IGNORED_ROOT_PATTERNS) are
    never flagged. ``root`` is parameterized for testability.
    """
    stray: list[str] = []
    for entry in sorted(p.name for p in root.iterdir()):
        if entry in IGNORED_ROOT_ENTRIES:
            continue
        if any(fnmatch.fnmatch(entry, pat) for pat in IGNORED_ROOT_PATTERNS):
            continue
        target = root / entry
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
