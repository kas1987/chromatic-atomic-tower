#!/usr/bin/env python3
"""Audit CAT mission registry for reconciliation sprints."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_yaml


def load_target(target_path: Path) -> dict:
    return load_yaml(target_path) if target_path.exists() else {}


ALLOWED_MISSION_STATUSES = {'approved', 'dispatched', 'in_progress', 'validating'}


def audit(registry_path: Path, target_path: Path | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    reg = load_yaml(registry_path)
    target = load_target(target_path) if target_path else {}

    active_id = reg.get('active_mission_id') or ''
    expected_active = target.get('canonical_active_mission_id')
    if expected_active is not None:
        expected_active = expected_active or ''
        if active_id != expected_active:
            errors.append(
                f'active_mission_id must be {expected_active!r}, found {active_id!r}'
            )

    missions = reg.get('missions') or []
    ids = [m.get('mission_id') for m in missions]
    seen: set[str] = set()
    for mid in ids:
        if mid in seen:
            errors.append(f'duplicate mission_id in registry: {mid}')
        seen.add(mid)

    required_missions = target.get('required_missions') or {}
    for mid in required_missions:
        if mid not in ids:
            errors.append(f'missing required mission {mid}')

    go_ready = [m for m in missions if m.get('status') in ALLOWED_MISSION_STATUSES]
    if expected_active is not None and (expected_active or ''):
        if len(go_ready) != 1:
            errors.append(f'expected exactly one GO-ready mission, found {len(go_ready)}')
        elif go_ready[0].get('mission_id') != expected_active:
            errors.append(
                f'active mission must be {expected_active}, found {go_ready[0].get("mission_id")}'
            )
    elif expected_active is not None:
        if go_ready:
            errors.append(
                f'expected no GO-ready missions during sprint_idle, found {len(go_ready)}'
            )

    repo_root = registry_path.resolve().parents[2]
    for m in missions:
        p = m.get('path')
        if p and not (repo_root / p).exists():
            errors.append(f'mission {m.get("mission_id")} path does not exist: {p}')

    return (not errors), errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--registry', default='missions/registry/MISSION_REGISTRY.yaml')
    ap.add_argument(
        '--target',
        default='docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml',
        help='Optional alignment target for active mission checks.',
    )
    args = ap.parse_args()
    root = ROOT
    target_path = root / args.target if args.target else None
    ok, errors = audit(root / args.registry, target_path)
    if ok:
        print('Registry audit passed.')
        return 0
    print('Registry audit failed:')
    for e in errors:
        print(f'- {e}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
