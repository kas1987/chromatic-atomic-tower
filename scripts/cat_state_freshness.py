#!/usr/bin/env python3
"""cat_state_freshness.py — detect drift between TOWER_STATE, MISSION_REGISTRY, and active files."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from common import ROOT, load_yaml, rel


@dataclass
class FreshnessResult:
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


def check_freshness(root: Path = ROOT) -> FreshnessResult:
    result = FreshnessResult()

    try:
        tower = load_yaml(root / 'state/TOWER_STATE.yaml')
    except Exception as exc:
        result.drift.append(f'TOWER_STATE.yaml unreadable: {exc}')
        return result

    try:
        registry = load_yaml(root / 'missions/registry/MISSION_REGISTRY.yaml')
    except Exception as exc:
        result.drift.append(f'MISSION_REGISTRY.yaml unreadable: {exc}')
        return result

    tower_mission = tower.get('active_mission_id')
    registry_mission = registry.get('active_mission_id')

    # Check 1: Tower active_mission_id matches registry
    if tower_mission == registry_mission:
        result.ok.append(f'active_mission_id matches: {tower_mission}')
    else:
        result.drift.append(
            f'active_mission_id mismatch: tower={tower_mission!r} registry={registry_mission!r}'
        )

    # Resolve active mission entry from registry
    missions = registry.get('missions', [])
    active_entry = next(
        (m for m in missions if m.get('mission_id') == registry_mission), None
    )

    # Check 2: Active mission file exists on disk
    if active_entry:
        mission_path = root / active_entry.get('path', '')
        if mission_path.exists():
            result.ok.append(f'active mission file exists: {rel(mission_path)}')
        else:
            result.drift.append(f'active mission file missing: {rel(mission_path)}')
    else:
        result.drift.append(
            f'active_mission_id {registry_mission!r} not found in registry missions list'
        )

    # Check 3: Tower active_bead_id matches registry current_bead_id
    # Normalize: treat None, '', and missing key all as "no active bead"
    tower_bead = tower.get('active_bead_id') or None
    registry_bead = (active_entry.get('current_bead_id') if active_entry else None) or None

    if tower_bead == registry_bead:
        result.ok.append(f'active_bead_id matches: {tower_bead}')
    else:
        result.drift.append(
            f'active_bead_id mismatch: tower={tower_bead!r} registry={registry_bead!r}'
        )

    # Check 4: Active BEAD file exists and its status field is "active"
    bead_id = tower_bead or registry_bead
    if bead_id:
        bead_path = root / f'beads/active/{bead_id}.yaml'
        if bead_path.exists():
            result.ok.append(f'active BEAD file exists: {rel(bead_path)}')
            try:
                bead_data = load_yaml(bead_path)
                bead_status = bead_data.get('status')
                if bead_status == 'active':
                    result.ok.append(f'active BEAD status is "active": {bead_id}')
                else:
                    result.drift.append(
                        f'active BEAD {bead_id} has status={bead_status!r}, expected "active"'
                    )
            except Exception as exc:
                result.drift.append(f'active BEAD file unreadable: {exc}')
        else:
            result.drift.append(f'active BEAD file missing: {rel(bead_path)}')
    else:
        result.ok.append('no active BEAD (bead_id is null)')

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check Tower state freshness against mission registry and BEAD files.'
    )
    parser.add_argument(
        '--write-report', action='store_true',
        help='Write report to evidence/tower/state_freshness_report.md',
    )
    args = parser.parse_args()

    result = check_freshness()
    report_text = result.report()
    print(report_text)

    if args.write_report:
        report_path = ROOT / 'evidence/tower/state_freshness_report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            f'# Tower State Freshness Report\n\n```\n{report_text}\n```\n',
            encoding='utf-8',
        )
        print(f'\nReport written: {rel(report_path)}')

    return 0 if result.is_fresh else 1


if __name__ == '__main__':
    raise SystemExit(main())
