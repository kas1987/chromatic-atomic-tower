#!/usr/bin/env python3
"""Generate a CAT evidence bundle skeleton for the current mission."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _current_mission(root: Path) -> str:
    tower = yaml.safe_load((root / 'state' / 'TOWER_STATE.yaml').read_text(encoding='utf-8')) or {}
    registry = yaml.safe_load((root / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml').read_text(encoding='utf-8')) or {}
    return str(tower.get('active_mission_id') or registry.get('active_mission_id') or 'unbound')


def _mission_path(root: Path, mission_id: str) -> str:
    matches = sorted((root / 'missions').glob(f'**/{mission_id}_*.yaml'))
    return str(matches[0].relative_to(root)) if matches else f'missions/active/{mission_id}_*.yaml'


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate a CAT evidence bundle skeleton.')
    parser.add_argument('--root', default='.', help='Repository root')
    parser.add_argument('--mission', default=None, help='Mission ID; defaults to the active mission')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    mission_id = args.mission or _current_mission(root)
    bundle = {
        'mission_id': mission_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'status': 'draft',
        'expected_files': [
            _mission_path(root, mission_id),
            'gates/assertion_gates.yaml',
            'agents/model_routes.yaml',
            'agents/skills/SKILL_REGISTRY.yaml',
            'evidence/templates/ASSERTION_EVIDENCE_MAP.yaml',
            'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md',
        ],
        'notes': 'Populate command outputs after CI/local validation runs.',
    }
    print(json.dumps(bundle, indent=2))

    if not args.dry_run:
        out = root / 'evidence' / 'reports' / f'{mission_id}_bundle_skeleton.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
