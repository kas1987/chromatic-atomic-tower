#!/usr/bin/env python3
from __future__ import annotations

import json
from common import ROOT, load_yaml


def main() -> int:
    registry = load_yaml(ROOT / 'missions/registry/MISSION_REGISTRY.yaml')
    tower = load_yaml(ROOT / 'state/TOWER_STATE.yaml')
    active = registry.get('active_mission_id')
    mission = next((m for m in registry.get('missions', []) if m.get('mission_id') == active), None)
    payload = {
        'tower_status': tower.get('status'),
        'active_sprint': tower.get('active_sprint'),
        'active_mission_id': active,
        'active_bead_id': tower.get('active_bead_id'),
        'mission': mission,
        'next_command': tower.get('next_command'),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
