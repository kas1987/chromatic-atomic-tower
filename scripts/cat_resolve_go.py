#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cat_align_common import normalize_bead_id
from cat_state_freshness import check_alignment
from common import ROOT, load_yaml, rel

ALLOWED_MISSION_STATUSES = {'approved', 'dispatched', 'in_progress', 'validating'}
ALLOWED_BEAD_STATUSES = {'active'}
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


def select_bead(mission: dict, beads: list[dict], *, allow_queued: bool) -> dict | None:
    mission_id = mission['mission_id']
    current = mission.get('current_bead_id')
    allowed = set(ALLOWED_BEAD_STATUSES)
    if allow_queued:
        allowed.add('queued')
    candidates = [b for b in beads if b.get('mission_id') == mission_id and b.get('status') in allowed]
    if current:
        for bead in candidates:
            if bead.get('bead_id') == current:
                return bead
    active = [b for b in candidates if b.get('status') == 'active']
    if active:
        return active[0]
    return None


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


def _git_head_short() -> str:
    try:
        r = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=ROOT, timeout=5,
        )
        sha = r.stdout.strip()
        return sha if len(sha) >= 7 else '0000000'
    except Exception:
        return '0000000'


def _append_go_decision(allowed: bool, drifts: list[str], sprint: str) -> None:
    log_path = ROOT / 'evidence' / 'logs' / 'go_decisions.jsonl'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'allowed': allowed,
        'drift_count': len(drifts),
        'drifts': drifts,
        'sprint': sprint,
        'commit_sha': _git_head_short(),
    }
    with log_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')


def _run_loghouse_self(strict: bool) -> int:
    """Call cat_loghouse.py --mode self in a subprocess. Returns its exit code."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'cat_loghouse.py'), '--mode', 'self']
    if strict:
        cmd.append('--strict')
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description='Resolve GO into the next CAT dispatch packet.')
    parser.add_argument('--json', action='store_true', help='Print JSON instead of Markdown.')
    parser.add_argument('--skip-align-check', action='store_true', help='Skip alignment gate (operator only).')
    parser.add_argument('--allow-queued', action='store_true', help='Allow queued BEAD dispatch (kickoff only).')
    parser.add_argument('--skip-loghouse', action='store_true', help='Skip LOGHOUSE self-monitor (operator only).')
    args = parser.parse_args()

    tower = load_yaml(ROOT / 'state/TOWER_STATE.yaml')
    sprint = tower.get('active_sprint', 'SPRINT-000')

    if not args.skip_align_check:
        alignment = check_alignment(ROOT)
        if not alignment.is_aligned:
            drifts = [d.split(']')[0].replace('[', '').strip() for d in alignment.report().splitlines() if 'DRIFT' in d]
            _append_go_decision(allowed=False, drifts=drifts, sprint=sprint)
            print('GO blocked: mission/BEAD state misaligned.')
            print(alignment.report())
            print('\nRemediation: python scripts/cat_align_check.py --strict')
            return 1

    registry = load_yaml(ROOT / 'missions/registry/MISSION_REGISTRY.yaml')
    mission = select_mission(registry)
    if not mission:
        print('No approved mission available.')
        return 1

    bead = select_bead(mission, load_active_beads(), allow_queued=args.allow_queued)
    if not bead:
        print(f"No active BEAD available for mission {mission.get('mission_id')}.")
        print('Use --allow-queued only for operator kickoff of a queued BEAD.')
        return 1

    if bead.get('status') != 'active' and not args.allow_queued:
        print(f"BEAD {bead.get('bead_id')} is {bead.get('status')!r}; only active BEADs dispatch.")
        return 1

    tower = load_yaml(ROOT / 'state/TOWER_STATE.yaml')
    tower_bead = normalize_bead_id(tower.get('active_bead_id'))
    selected = bead.get('bead_id', '')
    if tower_bead and tower_bead != selected:
        print(f"GO blocked: tower active_bead_id={tower_bead!r} != selected {selected!r}")
        return 1

    dispatch = build_dispatch(mission, bead)

    is_ready = dispatch['dispatch_status'] == 'ready'
    _append_go_decision(allowed=is_ready, drifts=[], sprint=sprint)

    if args.json:
        print(json.dumps(dispatch, indent=2))
    else:
        print_markdown(dispatch)

    if not is_ready:
        return 1

    # Run LOGHOUSE self-monitor after a successful GO resolution.
    if not args.skip_loghouse:
        lh_exit = _run_loghouse_self(strict=True)
        if lh_exit != 0:
            print('\nGO blocked: LOGHOUSE self-monitor detected critical governance findings.')
            print('Run: python scripts/cat_loghouse.py --mode self  for details.')
            return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
