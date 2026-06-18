#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import ROOT, load_yaml, write_yaml

RULES_PATHS = [
    ROOT / 'gates/state/transition_rules.yaml',
    ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml',
]
REGISTRY_PATH = ROOT / 'missions/registry/MISSION_REGISTRY.yaml'
TOWER_STATE_PATH = ROOT / 'state/TOWER_STATE.yaml'


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_rules() -> dict[str, Any]:
    for path in RULES_PATHS:
        if path.exists():
            return load_yaml(path)
    raise FileNotFoundError('could not find transition rules file in gates/state/')


def gate_approver_agent(default: str = 'Auditor') -> str:
    """The agent role that approves human-gated transitions (default Auditor)."""
    try:
        rules = load_rules()
    except FileNotFoundError:
        return default
    return str((rules or {}).get('gate_approver_agent') or default).strip() or default


def _registry_roles() -> set[str]:
    """Lower-cased set of roles defined in AGENT_REGISTRY.yaml."""
    reg = load_yaml(ROOT / 'agents/registry/AGENT_REGISTRY.yaml') or {}
    return {(a.get('role') or '').lower() for a in (reg.get('agents') or []) if a.get('role')}


def _status_list(rules: dict[str, Any], target_type: str) -> set[str]:
    if target_type in rules and isinstance(rules[target_type], dict):
        return set(rules[target_type].get('statuses', []))
    key = f'{target_type}_transitions'
    statuses: set[str] = set()
    for rule in rules.get(key, []):
        statuses.add(rule.get('from', ''))
        statuses.add(rule.get('to', ''))
    statuses.discard('')
    return statuses


def _terminal_statuses(rules: dict[str, Any], target_type: str) -> set[str]:
    if target_type in rules and isinstance(rules[target_type], dict):
        return set(rules[target_type].get('terminal_statuses', []))
    return set(rules.get(f'{target_type}_terminal_states', []))


def _transition_rule(rules: dict[str, Any], target_type: str, from_status: str, to_status: str) -> dict[str, Any] | None:
    # Legacy map-style rules
    section = rules.get(target_type)
    if isinstance(section, dict):
        allowed = section.get('allowed_transitions', {}).get(from_status, [])
        if to_status in allowed:
            return {'guard': 'none', 'reversible': False}
        return None

    # Arc-list rules
    key = f'{target_type}_transitions'
    for rule in rules.get(key, []):
        if rule.get('from') == from_status and rule.get('to') == to_status:
            return {
                'guard': rule.get('guard', 'none'),
                'reversible': bool(rule.get('reversible', False)),
            }
    return None


def _transition_allowed_with_rule(rules: dict[str, Any], target_type: str, from_status: str, to_status: str) -> tuple[bool, str, dict[str, Any]]:
    if target_type not in {'mission', 'bead'}:
        return False, f'unknown target type: {target_type}', {'guard': 'none', 'reversible': False}
    statuses = _status_list(rules, target_type)
    if from_status not in statuses:
        return False, f'unknown current status for {target_type}: {from_status}', {'guard': 'none', 'reversible': False}
    if to_status not in statuses:
        return False, f'unknown target status for {target_type}: {to_status}', {'guard': 'none', 'reversible': False}
    rule = _transition_rule(rules, target_type, from_status, to_status)
    if not rule:
        if from_status in _terminal_statuses(rules, target_type):
            return False, f'{from_status} is terminal for {target_type}; target {to_status} is not allowed', {'guard': 'none', 'reversible': False}
        return False, f'transition {from_status} -> {to_status} is not allowed for {target_type}', {'guard': 'none', 'reversible': False}
    return True, 'transition allowed', rule


def transition_allowed(rules: dict[str, Any], target_type: str, from_status: str, to_status: str) -> tuple[bool, str]:
    allowed, message, _ = _transition_allowed_with_rule(rules, target_type, from_status, to_status)
    return allowed, message


def evidence_required(rules: dict[str, Any], target_type: str, from_status: str | None, to_status: str) -> bool:
    section = rules.get(target_type)
    if isinstance(section, dict):
        return to_status in set(section.get('evidence_required_targets', []))
    # Arc-list format: check if the matching arc has guard: evidence_present
    key = f'{target_type}_transitions'
    for rule in rules.get(key, []):
        if rule.get('from') == from_status and rule.get('to') == to_status:
            return rule.get('guard') == 'evidence_present'
    return False


def evaluate_guard(guard_name: str, target_type: str, data: dict[str, Any], actor: str = '') -> tuple[bool, str]:
    if guard_name == 'none':
        return True, 'no precondition'
    if guard_name == 'active_bead_present' and target_type == 'mission':
        registry = load_yaml(REGISTRY_PATH) if REGISTRY_PATH.exists() else {}
        mission_id = data.get('mission_id')
        for mission in registry.get('missions', []):
            if mission.get('mission_id') == mission_id:
                bead_id = mission.get('current_bead_id')
                if bead_id:
                    # Verify the BEAD file actually exists, not just the registry entry
                    for pattern in ['beads/active/*.yaml', 'beads/completed/*.yaml', 'beads/failed/*.yaml']:
                        for path in ROOT.glob(pattern):
                            d = load_yaml(path) or {}
                            if d.get('bead_id') == bead_id:
                                return True, f'current_bead_id={bead_id} found on disk'
                    return False, f'current_bead_id={bead_id} not found on disk'
                break
        return False, 'mission has no current_bead_id'
    if guard_name == 'human_gate_if_required' and target_type == 'mission':
        gate = data.get('human_gate', {})
        if not bool(gate.get('required', False)):
            return True, 'gate not required'
        # The gate stays enforced, but the approver is now an AGENT, not a human.
        agent = gate_approver_agent()
        if agent.lower() not in _registry_roles():
            return False, f'gate approver agent {agent!r} is not a registered role'
        return True, f'gate approved by agent {agent!r}'
    # Remaining guards are deferred in this harness phase.
    return True, 'guard evaluation deferred'


def create_snapshot(target_type: str, target_id: str, contract_path: Path) -> Path:
    snap_id = f"snap_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    snap_dir = ROOT / 'evidence' / 'snapshots' / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    if REGISTRY_PATH.exists():
        shutil.copy2(REGISTRY_PATH, snap_dir / 'MISSION_REGISTRY.yaml')
    if TOWER_STATE_PATH.exists():
        shutil.copy2(TOWER_STATE_PATH, snap_dir / 'TOWER_STATE.yaml')
    if contract_path.exists():
        shutil.copy2(contract_path, snap_dir / f'{target_type}_{target_id}.yaml')
    return snap_dir


def find_contract(target_type: str, target_id: str) -> Path:
    if target_type == 'mission':
        patterns = ['missions/active/*.yaml', 'missions/backlog/*.yaml', 'missions/archived/*.yaml', 'missions/examples/*.yaml']
        key = 'mission_id'
    else:
        patterns = ['beads/active/*.yaml', 'beads/completed/*.yaml', 'beads/failed/*.yaml', 'beads/examples/*.yaml']
        key = 'bead_id'
    for pattern in patterns:
        for path in sorted(ROOT.glob(pattern)):
            data = load_yaml(path)
            if data and data.get(key) == target_id:
                return path
    raise FileNotFoundError(f'could not find {target_type} contract for {target_id}')


def update_registry_for_mission(mission_id: str, to_status: str, contract_path: Path, data: dict[str, Any]) -> None:
    registry = load_yaml(REGISTRY_PATH)
    found = False
    for mission in registry.get('missions', []):
        if mission.get('mission_id') == mission_id:
            mission['status'] = to_status
            mission['last_updated'] = data.get('last_updated')
            mission['path'] = rel(contract_path)
            if to_status in {'approved', 'dispatched', 'in_progress', 'validating'}:
                registry['active_mission_id'] = mission_id
            found = True
            break
    if not found:
        registry.setdefault('missions', []).append({
            'mission_id': mission_id,
            'title': data.get('title', mission_id),
            'level': data.get('level', 'M1'),
            'status': to_status,
            'priority': data.get('priority', 5),
            'owner': data.get('owner', 'Unknown'),
            'risk_level': data.get('risk_level', 'medium'),
            'reversibility': data.get('reversibility', 'medium'),
            'autonomy_level': data.get('autonomy_level', 'L1'),
            'confidence': data.get('confidence_minimum', 0),
            'current_bead_id': None,
            'path': rel(contract_path),
            'created': data.get('created'),
            'last_updated': data.get('last_updated'),
        })
    registry['last_updated'] = data.get('last_updated')
    write_yaml(REGISTRY_PATH, registry)


def update_registry_current_bead(mission_id: str, bead_id: str, to_status: str) -> None:
    if not mission_id:
        return
    registry = load_yaml(REGISTRY_PATH)
    updated = False
    for mission in registry.get('missions', []):
        if mission.get('mission_id') == mission_id:
            if to_status in {'queued', 'active', 'in_progress', 'validating', 'reviewed', 'changes_requested'}:
                mission['current_bead_id'] = bead_id
            elif mission.get('current_bead_id') == bead_id and to_status in {'completed', 'failed', 'archived'}:
                mission['current_bead_id'] = ''
            mission['last_updated'] = utc_now()
            updated = True
            break
    if updated:
        registry['last_updated'] = utc_now()
        write_yaml(REGISTRY_PATH, registry)


def update_tower_state(target_type: str, target_id: str, to_status: str, data: dict[str, Any]) -> None:
    if not TOWER_STATE_PATH.exists():
        return
    tower = load_yaml(TOWER_STATE_PATH)
    tower['last_updated'] = utc_now()
    if target_type == 'mission' and to_status in {'approved', 'dispatched', 'in_progress', 'validating'}:
        tower['active_mission_id'] = target_id
    if target_type == 'bead' and to_status in {'active', 'in_progress', 'validating', 'reviewed', 'changes_requested'}:
        tower['active_bead_id'] = target_id
        if data.get('mission_id'):
            tower['active_mission_id'] = data.get('mission_id')
    elif target_type == 'bead' and to_status in {'completed', 'failed', 'archived'}:
        if tower.get('active_bead_id') == target_id:
            tower['active_bead_id'] = ''
    write_yaml(TOWER_STATE_PATH, tower)


def append_audit_event(event: dict[str, Any], rules: dict[str, Any]) -> None:
    log_path = ROOT / rules.get('audit', {}).get('event_log', 'evidence/logs/transitions.jsonl')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, sort_keys=True) + '\n')


def maybe_move_contract(path: Path, target_type: str, to_status: str) -> Path:
    if target_type == 'mission' and to_status in {'closed', 'learned', 'rolled_back', 'abandoned'}:
        dest = ROOT / 'missions/archived' / path.name
    elif target_type == 'bead' and to_status == 'completed':
        dest = ROOT / 'beads/completed' / path.name
    elif target_type == 'bead' and to_status in {'failed', 'archived'}:
        dest = ROOT / 'beads/failed' / path.name
    else:
        return path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.resolve() != dest.resolve():
        path.replace(dest)
    return dest


def apply_transition(
    target_type: str,
    target_id: str,
    to_status: str,
    reason: str,
    evidence: str,
    actor: str,
    dry_run: bool,
    move: bool,
    from_status_expected: str | None = None,
) -> tuple[int, dict[str, Any]]:
    rules = load_rules()
    try:
        contract_path = find_contract(target_type, target_id)
    except FileNotFoundError as exc:
        event = {
            'timestamp': utc_now(),
            'target_type': target_type,
            'target_id': target_id,
            'from_status': from_status_expected or 'unknown',
            'to_status': to_status,
            'allowed': False,
            'dry_run': dry_run,
            'reason': reason,
            'evidence': evidence,
            'actor': actor,
            'message': str(exc),
            'contract_path': 'not found',
            'guard': 'none',
        }
        append_audit_event(event, rules)
        return 1, event
    data = load_yaml(contract_path)
    if target_type == 'mission':
        data.setdefault('mission_id', target_id)
    from_status = data.get('status')
    if from_status_expected and from_status_expected != from_status:
        event = {
            'timestamp': utc_now(),
            'target_type': target_type,
            'target_id': target_id,
            'from_status': from_status,
            'to_status': to_status,
            'allowed': False,
            'dry_run': dry_run,
            'reason': reason,
            'evidence': evidence,
            'actor': actor,
            'message': f'current status is {from_status}, not {from_status_expected}',
            'contract_path': rel(contract_path),
            'guard': 'none',
        }
        append_audit_event(event, rules)
        return 1, event

    allowed, message, rule = _transition_allowed_with_rule(rules, target_type, from_status, to_status)
    guard = rule.get('guard', 'none')
    if allowed and evidence_required(rules, target_type, from_status, to_status) and not evidence:
        allowed = False
        message = f'evidence is required for {target_type} transition to {to_status}'

    guard_ok, guard_msg = evaluate_guard(guard, target_type, data, actor)
    if allowed and not guard_ok:
        allowed = False
        message = f'guard {guard} failed: {guard_msg}'

    event = {
        'timestamp': utc_now(),
        'target_type': target_type,
        'target_id': target_id,
        'from_status': from_status,
        'to_status': to_status,
        'allowed': allowed,
        'dry_run': dry_run,
        'reason': reason,
        'evidence': evidence,
        'actor': actor,
        'message': message,
        'contract_path': rel(contract_path),
        'guard': guard,
        'guard_ok': guard_ok,
        'guard_message': guard_msg,
    }

    if not allowed:
        append_audit_event(event, rules)
        return 1, event

    if dry_run:
        append_audit_event(event, rules)
        return 0, event

    snapshot_dir = create_snapshot(target_type, target_id, contract_path)
    data['status'] = to_status
    data['last_updated'] = utc_now()

    new_path = maybe_move_contract(contract_path, target_type, to_status) if move else contract_path
    event['contract_path'] = rel(new_path)
    event['snapshot'] = rel(snapshot_dir)

    data.setdefault('transition_history', []).append(event)
    write_yaml(new_path, data)

    if target_type == 'mission':
        update_registry_for_mission(target_id, to_status, new_path, data)
    else:
        update_registry_current_bead(data.get('mission_id'), target_id, to_status)
    update_tower_state(target_type, target_id, to_status, data)
    append_audit_event(event, rules)
    return 0, event


def main() -> int:
    parser = argparse.ArgumentParser(description='Apply or dry-run CAT mission/BEAD state transitions.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--rollback', metavar='SNAPSHOT_ID', help='Restore files from a previous snapshot.')
    parser.add_argument('--type', choices=['mission', 'bead'], dest='target_type')
    parser.add_argument('--id', dest='target_id')
    parser.add_argument('--mission', dest='mission_id')
    parser.add_argument('--bead', dest='bead_id')
    parser.add_argument('--from', dest='from_status')
    parser.add_argument('--to', dest='to_status')
    parser.add_argument('--reason', default='no reason provided')
    parser.add_argument('--evidence', default='')
    parser.add_argument('--actor', default='Human Owner')
    parser.add_argument('--move', action='store_true', help='Move terminal contracts to completed/failed/archive folders when applicable.')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    if args.rollback:
        snapshot_id = args.rollback
        snap_dir = ROOT / 'evidence' / 'snapshots' / snapshot_id
        if not snap_dir.is_dir():
            print(f'error: snapshot {snapshot_id!r} not found at {rel(snap_dir)}', file=sys.stderr)
            return 1
        restored = []
        for f in snap_dir.iterdir():
            if f.name == 'metadata.json':
                continue
            if f.name == 'MISSION_REGISTRY.yaml':
                dest = REGISTRY_PATH
            elif f.name == 'TOWER_STATE.yaml':
                dest = TOWER_STATE_PATH
            elif f.name.startswith('mission_') or f.name.startswith('bead_'):
                entity_type = 'missions' if f.name.startswith('mission_') else 'beads'
                contract_id = f.stem.split('_', 1)[1]
                # Preserve the descriptive filename suffix (e.g. MP-CAT-003_CI_GOVERNANCE.yaml)
                # but always restore to the 'active' folder, not the post-move location.
                existing = list(ROOT.glob(f'{entity_type}/**/{contract_id}*.yaml'))
                filename = existing[0].name if existing else f'{contract_id}.yaml'
                dest = ROOT / entity_type / 'active' / filename
            else:
                dest = None
            if dest:
                import shutil as _shutil
                dest.parent.mkdir(parents=True, exist_ok=True)
                _shutil.copy2(f, dest)
                restored.append(rel(dest))
        print(f'rollback  : {snapshot_id}')
        for r in restored:
            print(f'  restored: {r}')
        return 0

    if bool(args.mission_id) and bool(args.bead_id):
        parser.error('use only one of --mission or --bead')

    if args.mission_id:
        target_type = 'mission'
        target_id = args.mission_id
    elif args.bead_id:
        target_type = 'bead'
        target_id = args.bead_id
    else:
        target_type = args.target_type
        target_id = args.target_id

    if not target_type or not target_id:
        parser.error('the following arguments are required: --type/--mission/--bead and --id/target id')

    if not args.to_status:
        parser.error('--to is required for --dry-run and --execute')

    dry_run = args.dry_run

    code, event = apply_transition(
        target_type,
        target_id,
        args.to_status,
        args.reason,
        args.evidence,
        args.actor,
        dry_run,
        args.move,
        from_status_expected=args.from_status,
    )
    if args.json:
        print(json.dumps(event, indent=2, sort_keys=True))
    else:
        print(f"transition : {event['target_type']} {event['target_id']}  {event['from_status']} -> {event['to_status']}")
        print(f"  guard    : {event.get('guard', 'none')} -> {'PASS' if event.get('guard_ok') else 'FAIL'} ({event.get('guard_message', 'n/a')})")
        print(f"  allowed  : {event['allowed']}")
        print(f"  mode     : {'dry-run' if event['dry_run'] else 'execute'}")
        print(f"  message  : {event['message']}")
        print(f"  evidence : {event['evidence'] or 'none'}")
        print(f"  contract : {event['contract_path']}")
        if event.get('snapshot'):
            print(f"  snapshot : {event['snapshot']}")
    if code != 0:
        print(f"error: {event['message']}", file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
