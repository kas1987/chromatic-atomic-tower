#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
try:
    from common import ROOT, rel
except ModuleNotFoundError:
    from scripts.common import ROOT, rel

REQUIRED_DIRS = [
    'evidence/ci', 'evidence/ci/runs', 'evidence/ci/reports', 'evidence/ci/summaries', 'evidence/ci/self-heal',
    'ci/reports', 'ci/rules', 'ci/templates',
]
FORBIDDEN_MARKERS = ['.env', 'secrets/', 'infra/prod/', 'production/', 'deploy/']

def build_plan() -> list[dict]:
    actions = []
    for item in REQUIRED_DIRS:
        path = ROOT / item
        if not path.exists():
            actions.append({'repair_class':'create_missing_required_directory','path':item,'safe':True,'description':f'Create required directory {item}'})
        gitkeep = path / '.gitkeep'
        if path.exists() and not gitkeep.exists():
            actions.append({'repair_class':'create_gitkeep_placeholder','path':f'{item}/.gitkeep','safe':True,'description':f'Create placeholder {item}/.gitkeep'})
    return actions

def apply_plan(actions: list[dict]) -> None:
    for action in actions:
        if not action.get('safe'):
            continue
        path_text = action['path']
        if any(marker in path_text for marker in FORBIDDEN_MARKERS):
            continue
        path = ROOT / path_text
        if action['repair_class'] == 'create_missing_required_directory':
            path.mkdir(parents=True, exist_ok=True)
        elif action['repair_class'] == 'create_gitkeep_placeholder':
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

def main() -> int:
    parser = argparse.ArgumentParser(description='Run bounded CAT self-healing validation.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    actions = build_plan()
    result = {'mode':'apply' if args.apply else 'dry-run','actions':actions,'action_count':len(actions),'safe_to_apply':all(a.get('safe') for a in actions),'rule':'Self-healing repairs structure, not truth.'}
    if args.apply:
        apply_plan(actions)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print('# CAT Self-Healing Validation')
        print()
        print(f"Mode: {result['mode']}")
        print(f"Actions: {result['action_count']}")
        print(f"Rule: {result['rule']}")
        for action in actions:
            print(f"- {action['repair_class']}: {action['path']} ({'safe' if action['safe'] else 'blocked'})")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
