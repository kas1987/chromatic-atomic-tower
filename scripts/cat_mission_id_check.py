#!/usr/bin/env python3
"""cat_mission_id_check.py — detect duplicate mission and BEAD IDs across the repo."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from cat_align_common import list_bead_ids, list_mission_contract_paths, mission_contract_collisions
from common import ROOT


def suggest_next_legacy_id(root: Path = ROOT) -> str:
    """Suggest next MP-CAT-NNN style ID from registry."""
    ids = list_mission_contract_paths(root)
    numbers = []
    for mid in ids:
        m = re.match(r'^MP-CAT-(\d+)$', mid)
        if m:
            numbers.append(int(m.group(1)))
    next_num = max(numbers, default=0) + 1
    return f'MP-CAT-{next_num:03d}'


def mission_id_exists(mission_id: str, root: Path = ROOT) -> bool:
    if mission_id in list_mission_contract_paths(root):
        return True
    registry_path = root / 'missions/registry/MISSION_REGISTRY.yaml'
    if registry_path.exists():
        from common import load_yaml
        registry = load_yaml(registry_path)
        return any(m.get('mission_id') == mission_id for m in registry.get('missions', []))
    return False


def check_collisions(root: Path = ROOT) -> tuple[list[dict], list[dict]]:
    mission_collisions = mission_contract_collisions(root)
    bead_collisions = []
    for bid, sources in sorted(list_bead_ids(root).items()):
        unique = sorted(set(sources))
        if len(unique) > 1:
            bead_collisions.append({'bead_id': bid, 'sources': unique})

    return mission_collisions, bead_collisions


def main() -> int:
    parser = argparse.ArgumentParser(description='Check for duplicate mission/BEAD IDs.')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--suggest-id', action='store_true', help='Print suggested next MP-CAT-NNN id.')
    args = parser.parse_args()

    if args.suggest_id:
        print(suggest_next_legacy_id())
        return 0

    mission_collisions, bead_collisions = check_collisions()
    report = {
        'mission_collisions': mission_collisions,
        'bead_collisions': bead_collisions,
        'status': 'fail' if mission_collisions or bead_collisions else 'pass',
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if mission_collisions:
            print('Mission ID collisions:')
            for item in mission_collisions:
                print(f"  {item['mission_id']}: {item['sources']}")
        if bead_collisions:
            print('BEAD ID collisions:')
            for item in bead_collisions:
                print(f"  {item['bead_id']}: {item['sources']}")
        if report['status'] == 'pass':
            print('No mission or BEAD ID collisions detected.')
        else:
            print(f"Suggested next legacy ID: {suggest_next_legacy_id()}")

    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
