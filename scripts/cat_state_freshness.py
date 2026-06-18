#!/usr/bin/env python3
"""cat_state_freshness.py — detect drift between TOWER_STATE, MISSION_REGISTRY, and contracts."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from cat_align_common import (
    BEAD_TERMINAL,
    MISSION_TERMINAL,
    AlignmentResult,
    DriftItem,
    beads_for_mission,
    find_bead_contract,
    find_mission_contract,
    is_post_sprint_idle,
    mission_contract_collisions,
    normalize_bead_id,
    normalize_mission_id,
)
from common import ROOT, load_yaml, rel

FreshnessResult = AlignmentResult


@dataclass
class LegacyFreshnessResult:
    drift: list[str] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)

    @property
    def is_fresh(self) -> bool:
        return not self.drift

    def report(self) -> str:
        lines = []
        for msg in self.ok:
            lines.append(f'OK    {msg}')
        for msg in self.drift:
            lines.append(f'DRIFT {msg}')
        if self.is_fresh:
            lines.append('State is FRESH — no drift detected.')
        else:
            lines.append(f'State is STALE — {len(self.drift)} drift(s) detected.')
        return '\n'.join(lines)


def check_alignment(root: Path = ROOT) -> AlignmentResult:
    result = AlignmentResult()

    try:
        tower = load_yaml(root / 'state/TOWER_STATE.yaml')
    except Exception as exc:
        result.drift.append(DriftItem('TOWER_UNREADABLE', f'TOWER_STATE.yaml unreadable: {exc}'))
        return result

    try:
        registry = load_yaml(root / 'missions/registry/MISSION_REGISTRY.yaml')
    except Exception as exc:
        result.drift.append(DriftItem('REGISTRY_UNREADABLE', f'MISSION_REGISTRY.yaml unreadable: {exc}'))
        return result

    tower_mission = normalize_mission_id(tower.get('active_mission_id'))
    registry_mission = normalize_mission_id(registry.get('active_mission_id'))

    if tower_mission == registry_mission:
        if tower_mission:
            result.ok.append(f'active_mission_id matches: {tower_mission}')
        else:
            result.ok.append('active_mission_id empty in tower and registry')
    else:
        result.drift.append(DriftItem(
            'MISSION_ID_MISMATCH',
            f'active_mission_id mismatch: tower={tower_mission!r} registry={registry_mission!r}',
            'Run cat_transition.py or cat_sprint_closeout.py to reconcile',
        ))

    missions = registry.get('missions', [])
    active_entry = next(
        (m for m in missions if m.get('mission_id') == registry_mission), None,
    ) if registry_mission else None

    if registry_mission:
        if active_entry:
            mission_path = root / active_entry.get('path', '')
            if mission_path.exists():
                result.ok.append(f'active mission file exists: {rel(mission_path)}')
            else:
                result.drift.append(DriftItem(
                    'MISSION_FILE_MISSING',
                    f'active mission file missing: {rel(mission_path)}',
                ))
        else:
            result.drift.append(DriftItem(
                'MISSION_NOT_IN_REGISTRY',
                f'active_mission_id {registry_mission!r} not found in registry missions list',
            ))

    tower_bead = normalize_bead_id(tower.get('active_bead_id'))
    registry_bead = normalize_bead_id(active_entry.get('current_bead_id') if active_entry else None)

    if tower_bead == registry_bead:
        if tower_bead:
            result.ok.append(f'active_bead_id matches: {tower_bead}')
        else:
            result.ok.append('no active BEAD (bead_id empty)')
    else:
        result.drift.append(DriftItem(
            'BEAD_ID_MISMATCH',
            f'active_bead_id mismatch: tower={tower_bead!r} registry={registry_bead!r}',
            'Normalize to empty string in both TOWER_STATE and registry',
        ))

    bead_id = tower_bead or registry_bead
    if bead_id:
        bead_data, bead_path, bead_folder = find_bead_contract(bead_id, root)
        if bead_path and bead_data:
            result.ok.append(f'BEAD file exists ({bead_folder}): {rel(bead_path)}')
            bead_status = bead_data.get('status')
            from cat_align_common import BEAD_ACTIVE_STATES
            if bead_status in BEAD_ACTIVE_STATES:
                result.ok.append(f'active BEAD status is in-flight ({bead_status!r}): {bead_id}')
            elif bead_status == 'queued':
                result.drift.append(DriftItem(
                    'BEAD_NOT_ACTIVE',
                    f'active BEAD {bead_id} has status={bead_status!r}, expected in-flight state',
                    'Transition queued -> active before GO dispatch',
                ))
            elif bead_status in BEAD_TERMINAL:
                result.drift.append(DriftItem(
                    'BEAD_TERMINAL_POINTER',
                    f'active BEAD {bead_id} is terminal (status={bead_status!r}, folder={bead_folder})',
                    'Clear current_bead_id and active_bead_id after BEAD closeout',
                ))
            else:
                result.drift.append(DriftItem(
                    'BEAD_NOT_ACTIVE',
                    f'active BEAD {bead_id} has status={bead_status!r}, expected in-flight state',
                ))
        else:
            result.drift.append(DriftItem('BEAD_FILE_MISSING', f'active BEAD file missing for {bead_id}'))

    if registry_mission and active_entry:
        contract, _ = find_mission_contract(registry_mission, root)
        if contract:
            reg_status = active_entry.get('status')
            contract_status = contract.get('status')
            if reg_status == contract_status:
                result.ok.append(f'mission status matches contract: {reg_status}')
            else:
                result.drift.append(DriftItem(
                    'REGISTRY_CONTRACT_STATUS_MISMATCH',
                    f'mission {registry_mission} status mismatch: registry={reg_status!r} contract={contract_status!r}',
                    'Use cat_transition.py — do not hand-edit status fields',
                ))

    if registry_mission and active_entry and not is_post_sprint_idle(tower):
        reg_status = active_entry.get('status')
        if reg_status in MISSION_TERMINAL:
            result.drift.append(DriftItem(
                'TERMINAL_MISSION_ACTIVE',
                f'active_mission_id {registry_mission} has terminal status={reg_status!r}',
                'Run cat_sprint_closeout.py or set tower status to sprint_idle',
            ))

    if registry_mission and active_entry and not is_post_sprint_idle(tower):
        reg_status = active_entry.get('status')
        if reg_status in {'approved', 'dispatched', 'in_progress', 'validating', 'reviewed'}:
            mission_beads = beads_for_mission(registry_mission, root)
            if mission_beads:
                all_terminal = all(status in BEAD_TERMINAL for _, status, _ in mission_beads)
                if all_terminal:
                    result.drift.append(DriftItem(
                        'MISSION_BEADS_COMPLETE_MISSION_OPEN',
                        f'mission {registry_mission} is {reg_status!r} but all {len(mission_beads)} BEADs are terminal',
                        'Run: python scripts/cat_sprint_closeout.py --mission ' + registry_mission + ' --execute',
                    ))

    for collision in mission_contract_collisions(root):
        result.drift.append(DriftItem(
            'MISSION_ID_COLLISION',
            f"mission_id {collision['mission_id']} appears in multiple contract files: {collision['sources']}",
            'Remove or rename duplicate; use cat_mission_id_check.py',
        ))

    return result


def check_freshness(root: Path = ROOT) -> LegacyFreshnessResult:
    aligned = check_alignment(root)
    legacy = LegacyFreshnessResult()
    legacy.ok = list(aligned.ok)
    legacy.drift = [
        f'[{item.code}] {item.message}' if item.code else item.message
        for item in aligned.drift
    ]
    return legacy


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check Tower state freshness against mission registry and BEAD files.',
    )
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args()

    result = check_alignment()
    print(result.report())

    if args.write_report:
        report_path = ROOT / 'evidence/tower/state_freshness_report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(f'# State Freshness Report\n\n```\n{result.report()}\n```\n', encoding='utf-8')
        print(f'Report written: {rel(report_path)}')

    return 0 if result.is_aligned else 1


if __name__ == '__main__':
    raise SystemExit(main())
