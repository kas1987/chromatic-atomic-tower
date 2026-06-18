#!/usr/bin/env python3
"""cat_mission_package.py — read-only Mission Package assembler.

Produces a review-ready "mission package" record for a given mission: its
contract metadata, constituent BEADs, bead summary counts, declared evidence
references, and next-steps hints.

This tool is **read-only by default**: it never mutates the registry, tower
state, or any BEAD contract. (Background-systems rule: report, never
auto-implement.)  Pass ``--emit`` to additionally persist the package record
under ``evidence/packages/``.

Usage:
    python scripts/cat_mission_package.py                # active mission
    python scripts/cat_mission_package.py --mission ID   # specific mission
    python scripts/cat_mission_package.py --json         # machine-readable
    python scripts/cat_mission_package.py --emit         # write evidence/packages/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cat_align_common import BEAD_TERMINAL, beads_for_mission, find_mission_contract
from common import ROOT, load_yaml, rel, utc_now

TOWER_STATE_PATH = ROOT / 'state/TOWER_STATE.yaml'
REGISTRY_PATH = ROOT / 'missions/registry/MISSION_REGISTRY.yaml'
EVIDENCE_DIR = ROOT / 'evidence/packages'


def _active_mission_id() -> str:
    if not TOWER_STATE_PATH.exists():
        return ''
    tower = load_yaml(TOWER_STATE_PATH) or {}
    return (tower.get('active_mission_id') or '').strip()


def _registry_entry(mission_id: str) -> dict | None:
    reg = load_yaml(REGISTRY_PATH) or {}
    for m in reg.get('missions', []) or []:
        if m.get('mission_id') == mission_id:
            return m
    return None


def build_package(mission_id: str) -> dict:
    """Assemble a mission package record for ``mission_id`` (pure / read-only)."""

    # --- contract and registry ---
    reg_entry = _registry_entry(mission_id) if mission_id else None
    contract, _ = find_mission_contract(mission_id, ROOT) if mission_id else (None, None)

    mission_title = ''
    mission_status = ''
    if contract:
        mission_title = contract.get('title', '')
        mission_status = contract.get('status', '')
    elif reg_entry:
        mission_title = reg_entry.get('title', '')
        mission_status = reg_entry.get('status', '')

    # --- beads ---
    raw_beads = beads_for_mission(mission_id, ROOT) if mission_id else []

    bead_records: list[dict] = []
    evidence_refs: list[str] = []
    terminal_count = 0

    for bead_id, status, bead_path in raw_beads:
        bead_data: dict = {}
        if isinstance(bead_path, Path) and bead_path.exists():
            bead_data = load_yaml(bead_path) or {}

        agent_role = bead_data.get('agent_role', '')
        bead_records.append({
            'bead_id': bead_id,
            'status': status,
            'agent_role': agent_role,
        })

        if status in BEAD_TERMINAL:
            terminal_count += 1

        # collect declared validation evidence paths that exist on disk
        for v in (bead_data.get('validation') or []):
            ep = v.get('evidence_path')
            if ep and (ROOT / ep).exists():
                ref = rel(ROOT / ep)
                if ref not in evidence_refs:
                    evidence_refs.append(ref)

    # --- bead summary ---
    total = len(bead_records)
    completed_count = sum(1 for b in bead_records if b['status'] == 'completed')
    bead_summary = {
        'total': total,
        'completed': completed_count,
        'terminal': terminal_count,
    }

    # --- next_steps ---
    if not mission_id:
        next_steps = ['no mission selected — pass --mission <ID>']
    elif mission_status in BEAD_TERMINAL or mission_status in ('closed', 'learned', 'abandoned'):
        next_steps = ['mission closed']
    else:
        non_terminal = [b for b in bead_records if b['status'] not in BEAD_TERMINAL]
        if non_terminal:
            ids = ', '.join(b['bead_id'] for b in non_terminal)
            next_steps = [f'{len(non_terminal)} non-terminal BEAD(s) remain: {ids}']
        else:
            next_steps = ['all BEADs terminal — ready to close mission']

    return {
        'kind': 'mission_package',
        'timestamp': utc_now(),
        'mission_id': mission_id or None,
        'mission_title': mission_title or None,
        'mission_status': mission_status or None,
        'beads': bead_records,
        'bead_summary': bead_summary,
        'evidence_refs': evidence_refs,
        'next_steps': next_steps,
    }


def _print_human(record: dict) -> None:
    mid = record['mission_id'] or '(none — tower sprint_idle)'
    title = record['mission_title'] or ''
    status = record['mission_status'] or 'unknown'
    bs = record['bead_summary']
    print(f'Mission Package — {mid}')
    if title:
        print(f'  title:  {title}')
    print(f'  status: {status}  |  BEADs: {bs["total"]} total, '
          f'{bs["completed"]} completed, {bs["terminal"]} terminal')
    for ns in record['next_steps']:
        print(f'  next:   {ns}')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Read-only Mission Package assembler.'
    )
    parser.add_argument(
        '--mission', default='',
        help='Mission ID (default: active mission from tower)'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Emit the package record as JSON'
    )
    parser.add_argument(
        '--emit', action='store_true',
        help='Persist the package record under evidence/packages/'
    )
    args = parser.parse_args()

    mission_id = args.mission.strip() or _active_mission_id()
    record = build_package(mission_id)

    if args.json:
        print(json.dumps(record, indent=2))
    else:
        _print_human(record)

    if args.emit:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        slug = (mission_id or 'idle').replace('/', '_')
        out = EVIDENCE_DIR / f'mission_package_{slug}.json'
        out.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(f'\nwrote {rel(out)}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
