#!/usr/bin/env python3
"""cat_go.py — read-only GO-mode pipeline status driver.

Implements the spine of the Chromatic Atomic Harness **END-TO-END GO-MODE
PIPELINE**: for one mission it evaluates which of the seven stages are
satisfied and emits a single auditable run record.

    1. Intent            2. Mission Pack      3. Plan & Decompose
    4. Execute           5. Observe & Capture 6. Score & Validate
    7. Continue / Close

This driver is **read-only by default**: it inspects tower state, the mission
registry, the mission's BEADs, and evidence — it never mutates state, registry,
or BEAD contracts. (Background-systems rule: report, never auto-implement.)
Pass ``--emit`` to additionally persist the run record under ``evidence/go/``.

Usage:
    python scripts/cat_go.py                 # status of the active mission
    python scripts/cat_go.py --mission ID    # status of a specific mission
    python scripts/cat_go.py --json          # machine-readable record
    python scripts/cat_go.py --emit          # also write evidence/go/<id>.json
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
EVIDENCE_DIR = ROOT / 'evidence/go'

STAGES = [
    'intent',
    'mission_pack',
    'plan_decompose',
    'execute',
    'observe_capture',
    'score_validate',
    'continue_close',
]

# BEAD statuses that mean work has started / progressed past dispatch.
_STARTED = frozenset({'in_progress', 'validating', 'reviewed', 'completed', 'archived', 'failed'})
# BEAD statuses that mean the BEAD has cleared the score/validate stage.
_VALIDATED = frozenset({'validating', 'reviewed', 'completed', 'archived'})
_MISSION_TERMINAL = frozenset({'closed', 'learned', 'abandoned'})


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


def _bead_has_evidence(bead_data: dict) -> bool:
    """True if any of the BEAD's declared validation evidence paths exist."""
    for v in (bead_data or {}).get('validation', []) or []:
        ep = v.get('evidence_path')
        if ep and (ROOT / ep).exists():
            return True
    return False


def evaluate(mission_id: str) -> dict:
    """Evaluate the 7 GO-mode stages for ``mission_id`` (pure / read-only)."""
    stages: dict[str, dict] = {}

    def mark(name: str, status: str, detail: str) -> None:
        stages[name] = {'status': status, 'detail': detail}

    # 1. Intent — an intent has been selected into the tower.
    if mission_id:
        mark('intent', 'satisfied', f'mission {mission_id} selected')
    else:
        mark('intent', 'pending', 'no active mission (tower sprint_idle)')

    contract, contract_path = (None, None)
    if mission_id:
        contract, contract_path = find_mission_contract(mission_id, ROOT)

    # 2. Mission Pack — a valid mission contract exists.
    if contract is not None:
        mark('mission_pack', 'satisfied', rel(contract_path) if contract_path else 'contract loaded')
    elif mission_id:
        mark('mission_pack', 'pending', 'mission contract not found')
    else:
        mark('mission_pack', 'na', 'no mission')

    beads = beads_for_mission(mission_id, ROOT) if mission_id else []
    statuses = [s for _, s, _ in beads]

    # 3. Plan & Decompose — the mission is broken into BEADs.
    if beads:
        mark('plan_decompose', 'satisfied', f'{len(beads)} BEAD(s)')
    elif mission_id:
        mark('plan_decompose', 'pending', 'no BEADs decomposed')
    else:
        mark('plan_decompose', 'na', 'no mission')

    # 4. Execute — at least one BEAD has progressed past dispatch.
    started = [s for s in statuses if s in _STARTED]
    if beads and started:
        mark('execute', 'satisfied', f'{len(started)}/{len(beads)} BEAD(s) started')
    elif beads:
        mark('execute', 'pending', 'BEADs queued, none started')
    else:
        mark('execute', 'na', 'no BEADs')

    # 5. Observe & Capture — evidence exists for the BEADs.
    with_evidence = 0
    for _, _, bead_path in beads:
        bd = load_yaml(bead_path) if isinstance(bead_path, Path) and bead_path.exists() else {}
        if _bead_has_evidence(bd):
            with_evidence += 1
    if beads and with_evidence:
        mark('observe_capture', 'satisfied', f'{with_evidence}/{len(beads)} BEAD(s) have evidence')
    elif beads:
        mark('observe_capture', 'pending', 'no BEAD evidence found')
    else:
        mark('observe_capture', 'na', 'no BEADs')

    # 6. Score & Validate — every BEAD has cleared the validate stage.
    if beads and all(s in _VALIDATED for s in statuses):
        mark('score_validate', 'satisfied', 'all BEADs validated')
    elif beads:
        pending = [s for s in statuses if s not in _VALIDATED]
        mark('score_validate', 'pending', f'{len(pending)} BEAD(s) not yet validated')
    else:
        mark('score_validate', 'na', 'no BEADs')

    # 7. Continue / Close — mission terminal or all BEADs terminal.
    reg_entry = _registry_entry(mission_id) if mission_id else None
    mission_status = (reg_entry or {}).get('status', '')
    all_terminal = bool(beads) and all(s in BEAD_TERMINAL for s in statuses)
    if mission_status in _MISSION_TERMINAL:
        mark('continue_close', 'satisfied', f'mission {mission_status}')
    elif all_terminal:
        mark('continue_close', 'satisfied', 'all BEADs terminal — ready to close')
    elif mission_id:
        mark('continue_close', 'pending', 'mission open')
    else:
        mark('continue_close', 'na', 'no mission')

    satisfied = sum(1 for s in stages.values() if s['status'] == 'satisfied')
    return {
        'kind': 'go_run_record',
        'timestamp': utc_now(),
        'mission_id': mission_id or None,
        'mission_status': mission_status or None,
        'bead_count': len(beads),
        'stages': stages,
        'stages_satisfied': satisfied,
        'stages_total': len(STAGES),
    }


_GLYPH = {'satisfied': '[x]', 'pending': '[ ]', 'na': '[-]'}


def _print_human(record: dict) -> None:
    mid = record['mission_id'] or '(none — tower sprint_idle)'
    print(f'GO-mode pipeline — mission {mid}')
    print(f'  {record["stages_satisfied"]}/{record["stages_total"]} stages satisfied'
          f' · {record["bead_count"]} BEAD(s)'
          + (f' · mission {record["mission_status"]}' if record['mission_status'] else ''))
    print()
    for i, name in enumerate(STAGES, 1):
        st = record['stages'][name]
        print(f'  {i}. {_GLYPH[st["status"]]} {name:<16} {st["detail"]}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only GO-mode pipeline status driver.')
    parser.add_argument('--mission', default='', help='Mission ID (default: active mission from tower)')
    parser.add_argument('--json', action='store_true', help='Emit the run record as JSON')
    parser.add_argument('--emit', action='store_true', help='Persist the run record under evidence/go/')
    args = parser.parse_args()

    mission_id = args.mission.strip() or _active_mission_id()
    record = evaluate(mission_id)

    if args.json:
        print(json.dumps(record, indent=2))
    else:
        _print_human(record)

    if args.emit:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        slug = (mission_id or 'idle').replace('/', '_')
        out = EVIDENCE_DIR / f'go_run_{slug}.json'
        out.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        print(f'\nwrote {rel(out)}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
