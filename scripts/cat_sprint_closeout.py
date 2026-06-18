#!/usr/bin/env python3
"""cat_sprint_closeout.py — close a mission when all BEADs are terminal (direct update)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cat_align_common import BEAD_TERMINAL, beads_for_mission, find_mission_contract
from common import ROOT, load_yaml, rel, utc_now, write_yaml

REGISTRY_PATH = ROOT / 'missions/registry/MISSION_REGISTRY.yaml'
TOWER_STATE_PATH = ROOT / 'state/TOWER_STATE.yaml'


def _append_audit(event: dict) -> None:
    log_path = ROOT / 'evidence/logs/transitions.jsonl'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, sort_keys=True) + '\n')


def closeout_mission(mission_id: str, *, dry_run: bool, evidence: str, actor: str) -> int:
    contract, contract_path = find_mission_contract(mission_id, ROOT)
    if not contract or not contract_path:
        print(f'error: mission {mission_id} not found')
        return 1

    status = contract.get('status')
    mission_beads = beads_for_mission(mission_id, ROOT)
    non_terminal = [(bid, st) for bid, st, _ in mission_beads if st not in BEAD_TERMINAL]
    if non_terminal:
        print(f'error: mission {mission_id} has non-terminal BEADs: {non_terminal}')
        return 1

    if status in {'closed', 'learned', 'abandoned'}:
        print(f'mission {mission_id} already terminal: {status}')
        return 0

    print(f'Closing mission {mission_id} (status: {status}, {len(mission_beads)} terminal BEADs)')

    if dry_run:
        print('Dry-run: would set mission status=closed, tower=sprint_idle, clear pointers')
        return 0

    now = utc_now()
    from_status = status
    contract['status'] = 'closed'
    contract['last_updated'] = now
    contract.setdefault('transition_history', []).append({
        'timestamp': now,
        'target_type': 'mission',
        'target_id': mission_id,
        'from_status': from_status,
        'to_status': 'closed',
        'allowed': True,
        'dry_run': False,
        'reason': 'Sprint closeout — all BEADs terminal',
        'evidence': evidence,
        'actor': actor,
        'message': 'direct closeout via cat_sprint_closeout.py',
        'contract_path': rel(contract_path),
        'guard': 'mission_all_beads_terminal',
        'guard_ok': True,
    })

    dest = ROOT / 'missions/archived' / contract_path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if contract_path.resolve() != dest.resolve():
        write_yaml(dest, contract)
        contract_path.unlink(missing_ok=True)
        contract_path = dest
    else:
        write_yaml(contract_path, contract)

    registry = load_yaml(REGISTRY_PATH)
    registry['active_mission_id'] = ''
    registry['last_updated'] = now
    for mission in registry.get('missions', []):
        if mission.get('mission_id') == mission_id:
            mission['status'] = 'closed'
            mission['current_bead_id'] = ''
            mission['last_updated'] = now
            mission['path'] = rel(contract_path)
    write_yaml(REGISTRY_PATH, registry)

    if TOWER_STATE_PATH.exists():
        tower = load_yaml(TOWER_STATE_PATH)
        tower['status'] = 'sprint_idle'
        tower['active_mission_id'] = ''
        tower['active_bead_id'] = ''
        tower['last_updated'] = now
        write_yaml(TOWER_STATE_PATH, tower)
        print(f'Updated {rel(TOWER_STATE_PATH)} to sprint_idle')

    _append_audit({
        'timestamp': now,
        'target_type': 'mission',
        'target_id': mission_id,
        'from_status': from_status,
        'to_status': 'closed',
        'allowed': True,
        'dry_run': False,
        'reason': 'Sprint closeout — all BEADs terminal',
        'evidence': evidence,
        'actor': actor,
        'message': 'direct closeout via cat_sprint_closeout.py',
        'contract_path': rel(contract_path),
    })

    render_cmd = [sys.executable, 'scripts/cat_render_sprint_state.py']
    subprocess_result = __import__('subprocess').run(render_cmd, cwd=ROOT, check=False)
    if subprocess_result.returncode != 0:
        print('warning: cat_render_sprint_state.py failed', file=sys.stderr)

    _score_beads_on_closeout(mission_beads, dry_run=False)

    print(f'Mission {mission_id} closeout complete -> closed')
    return 0


def _score_beads_on_closeout(mission_beads: list, *, dry_run: bool) -> None:
    """Call cat_agent_scorecard score-bead for each terminal BEAD (dry-run by default)."""
    import subprocess as sp
    scorecard_script = ROOT / 'scripts' / 'cat_agent_scorecard.py'
    if not scorecard_script.exists():
        return
    for bead_id, status, bead_path in mission_beads:
        bead_data = load_yaml(bead_path) if isinstance(bead_path, Path) and bead_path.exists() else {}
        role = ((bead_data or {}).get('agent_role') or 'Builder')
        if status == 'archived':
            continue
        result = 'completed' if status == 'completed' else 'failed'
        mode = '--dry-run' if dry_run else '--execute'
        cmd = [
            sys.executable, str(scorecard_script),
            mode, 'score-bead',
            '--role', role,
            '--bead', bead_id,
            '--result', result,
        ]
        proc = sp.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode != 0:
            print(f'warning: scorecard update failed for {bead_id}: {proc.stderr.strip()}', file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description='Close a mission when all BEADs are terminal.')
    parser.add_argument('--mission', required=True, help='Mission ID to close')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--evidence', default='evidence/reports/sprint_closeout.md')
    parser.add_argument('--actor', default='Human Owner')
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print('error: specify --dry-run or --execute')
        return 1

    return closeout_mission(
        args.mission,
        dry_run=args.dry_run,
        evidence=args.evidence,
        actor=args.actor,
    )


if __name__ == '__main__':
    raise SystemExit(main())
