#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, load_yaml, rel

ALLOWED_MISSION_STATUSES = {'approved', 'dispatched', 'in_progress', 'validating'}
ALLOWED_BEAD_STATUSES = {'active', 'queued'}
RISK_ORDER = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}


def load_active_beads() -> list[dict]:
    beads = []
    for path in sorted((ROOT / 'beads/active').glob('*.yaml')):
        data = load_yaml(path)
        data['_path'] = rel(path)
        beads.append(data)
    return beads


def select_mission(registry: dict) -> dict | None:
    candidates = [m for m in registry.get('missions', []) if m.get('status') in ALLOWED_MISSION_STATUSES]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda m: (
            int(m.get('priority', 5)),
            -int(m.get('confidence', 0)),
            RISK_ORDER.get(str(m.get('risk_level', 'critical')), 9),
            str(m.get('created', '9999-99-99')),
        ),
    )[0]


def select_bead(mission: dict, beads: list[dict]) -> dict | None:
    mission_id = mission['mission_id']
    current = mission.get('current_bead_id')
    candidates = [b for b in beads if b.get('mission_id') == mission_id and b.get('status') in ALLOWED_BEAD_STATUSES]
    if current:
        for bead in candidates:
            if bead.get('bead_id') == current:
                return bead
    active = [b for b in candidates if b.get('status') == 'active']
    if active:
        return active[0]
    return candidates[0] if candidates else None


def confidence_band(score: int) -> str:
    if score >= 90:
        return 'very_high'
    if score >= 75:
        return 'high'
    if score >= 60:
        return 'medium'
    if score >= 40:
        return 'low'
    return 'blocked'


def build_dispatch(mission: dict, bead: dict) -> dict:
    score = int(bead.get('confidence', {}).get('current', 0))
    minimum = int(bead.get('confidence', {}).get('minimum', 0))
    blocked = score < minimum
    return {
        'dispatch_status': 'blocked' if blocked else 'ready',
        'reason': 'confidence below minimum' if blocked else 'highest-priority approved mission and active BEAD selected',
        'mission_id': mission.get('mission_id'),
        'mission_title': mission.get('title'),
        'mission_level': mission.get('level'),
        'mission_risk': mission.get('risk_level'),
        'bead_id': bead.get('bead_id'),
        'bead_title': bead.get('title'),
        'bead_status': bead.get('status'),
        'agent_role': bead.get('agent_role'),
        'autonomy_level': bead.get('autonomy_level'),
        'confidence': score,
        'confidence_minimum': minimum,
        'confidence_band': confidence_band(score),
        'risk_level': bead.get('risk_level'),
        'reversibility': bead.get('reversibility'),
        'allowed_paths': bead.get('allowed_paths', []),
        'forbidden_paths': bead.get('forbidden_paths', []),
        'tool_budget': bead.get('tool_budget', {}),
        'definition_of_done': bead.get('definition_of_done', []),
        'validation': bead.get('validation', []),
        'stop_conditions': bead.get('stop_conditions', []),
        'required_output': bead.get('required_output', []),
        'bead_path': bead.get('_path'),
        'mission_path': mission.get('path'),
    }


def print_markdown(dispatch: dict) -> None:
    print('# CAT GO Dispatch Packet')
    print()
    print(f"Status: {dispatch['dispatch_status']}")
    print(f"Reason: {dispatch['reason']}")
    print()
    print(f"Mission: {dispatch['mission_id']} - {dispatch['mission_title']}")
    print(f"BEAD: {dispatch['bead_id']} - {dispatch['bead_title']}")
    print(f"Agent Role: {dispatch['agent_role']}")
    print(f"Autonomy: {dispatch['autonomy_level']}")
    print(f"Confidence: {dispatch['confidence']} / minimum {dispatch['confidence_minimum']} ({dispatch['confidence_band']})")
    print(f"Risk: {dispatch['risk_level']}")
    print(f"Reversibility: {dispatch['reversibility']}")
    print()
    print('## Allowed Paths')
    for item in dispatch['allowed_paths']:
        print(f'- {item}')
    print()
    print('## Forbidden Paths')
    for item in dispatch['forbidden_paths']:
        print(f'- {item}')
    print()
    print('## Tool Budget')
    for key, value in dispatch['tool_budget'].items():
        print(f'- {key}: {value}')
    print()
    print('## Definition of Done')
    for item in dispatch['definition_of_done']:
        print(f'- {item}')
    print()
    print('## Validation')
    for item in dispatch['validation']:
        print(f"- {item.get('type')}: `{item.get('command')}` -> {item.get('evidence_path')}")
    print()
    print('## Stop Conditions')
    for item in dispatch['stop_conditions']:
        print(f'- {item}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Resolve GO into the next CAT dispatch packet.')
    parser.add_argument('--json', action='store_true', help='Print JSON instead of Markdown.')
    args = parser.parse_args()

    registry = load_yaml(ROOT / 'missions/registry/MISSION_REGISTRY.yaml')
    mission = select_mission(registry)
    if not mission:
        print('No approved mission available.')
        return 1

    bead = select_bead(mission, load_active_beads())
    if not bead:
        print(f"No active or queued BEAD available for mission {mission.get('mission_id')}.")
        return 1

    dispatch = build_dispatch(mission, bead)
    if args.json:
        print(json.dumps(dispatch, indent=2))
    else:
        print_markdown(dispatch)
    return 0 if dispatch['dispatch_status'] == 'ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
