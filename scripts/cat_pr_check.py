#!/usr/bin/env python3
from __future__ import annotations
import argparse, fnmatch, json, os, sys
from pathlib import Path
try:
    from common import ROOT, load_yaml, rel
except ModuleNotFoundError:
    from scripts.common import ROOT, load_yaml, rel

FORBIDDEN_DEFAULTS = ['.env', '.env.*', 'secrets/**', 'infra/prod/**', 'production/**', 'deploy/**']

def load_bead(bead_id: str) -> tuple[dict | None, Path | None]:
    for base in ['beads/active', 'beads/examples', 'beads/completed']:
        for path in sorted((ROOT / base).glob('*.yaml')):
            data = load_yaml(path)
            if data.get('bead_id') == bead_id:
                return data, path
    return None, None

def load_changed_files(path: str | None) -> list[str]:
    if path:
        file_path = ROOT / path if not os.path.isabs(path) else Path(path)
        return [line.strip() for line in file_path.read_text(encoding='utf-8').splitlines() if line.strip() and not line.strip().startswith('#')]
    env_value = os.getenv('CAT_CHANGED_FILES', '')
    if env_value:
        return [item.strip() for item in env_value.split(',') if item.strip()]
    return []

def matches(pattern: str, file_path: str) -> bool:
    if pattern.endswith('/**'):
        return file_path.startswith(pattern[:-3])
    if pattern.endswith('*') or '*' in pattern:
        return fnmatch.fnmatch(file_path, pattern)
    return file_path == pattern or file_path.startswith(pattern.rstrip('/') + '/')

def check_scope(mission_id: str, bead_id: str, changed_files: list[str]) -> dict:
    bead, bead_path = load_bead(bead_id)
    failures: list[str] = []
    if not mission_id:
        failures.append('missing mission id')
    if not bead_id:
        failures.append('missing bead id')
    if bead is None:
        return {'status': 'failed', 'mission_id': mission_id, 'bead_id': bead_id, 'changed_files': changed_files, 'failures': [f'unknown bead: {bead_id}']}
    if bead.get('mission_id') != mission_id:
        failures.append(f'bead belongs to {bead.get("mission_id")}, not {mission_id}')

    allowed = bead.get('allowed_paths', [])
    forbidden = list(FORBIDDEN_DEFAULTS) + bead.get('forbidden_paths', [])
    for file_path in changed_files:
        if any(matches(pattern, file_path) for pattern in forbidden):
            failures.append(f'forbidden path changed: {file_path}')
        elif not any(matches(pattern, file_path) for pattern in allowed):
            failures.append(f'outside allowed paths: {file_path}')
    return {
        'status': 'failed' if failures else 'passed',
        'mission_id': mission_id,
        'bead_id': bead_id,
        'bead_path': rel(bead_path) if bead_path else None,
        'changed_files': changed_files,
        'allowed_paths': allowed,
        'forbidden_paths': forbidden,
        'failures': failures,
    }

def print_markdown(result: dict) -> None:
    print('# CAT PR Scope Check')
    print()
    print(f"Status: {result['status']}")
    print(f"Mission: {result.get('mission_id')}")
    print(f"BEAD: {result.get('bead_id')}")
    print()
    print('## Changed Files')
    for item in result.get('changed_files', []): print(f'- {item}')
    if result.get('failures'):
        print('\n## Failures')
        for item in result['failures']: print(f'- {item}')

def _detect_active_ids() -> tuple[str, str]:
    tower_path = ROOT / 'state' / 'TOWER_STATE.yaml'
    if tower_path.exists():
        tower = load_yaml(tower_path)
        return tower.get('active_mission_id', ''), tower.get('active_bead_id', '')
    return '', ''


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate PR changed files against BEAD scope.')
    parser.add_argument('--mission', default='')
    parser.add_argument('--bead', default='')
    parser.add_argument('--changed-files', help='Path to newline-delimited changed files list.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    mission_id = args.mission
    bead_id = args.bead
    if not mission_id or not bead_id:
        detected_mission, detected_bead = _detect_active_ids()
        mission_id = mission_id or detected_mission
        bead_id = bead_id or detected_bead
    if not mission_id or not bead_id:
        print('warning: no active mission/BEAD in tower state — skipping scope check', file=sys.stderr)
        return 0
    result = check_scope(mission_id, bead_id, load_changed_files(args.changed_files))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_markdown(result)
    return 0 if result['status'] == 'passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
