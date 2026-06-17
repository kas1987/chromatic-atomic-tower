#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from common import ROOT, load_yaml, rel
    from cat_evidence import validate_bundle
    from cat_transition import apply_transition
except ModuleNotFoundError:  # pragma: no cover
    from scripts.common import ROOT, load_yaml, rel
    from scripts.cat_evidence import validate_bundle
    from scripts.cat_transition import apply_transition

RULES_PATH = ROOT / 'gates/evidence/EVIDENCE_GATE_RULES.yaml'


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_rules() -> dict[str, Any]:
    return load_yaml(RULES_PATH)


def write_closeout_report(event: dict[str, Any], bundle_data: dict[str, Any], errors: list[str]) -> Path:
    rules = load_rules()
    report_dir = ROOT / rules.get('audit', {}).get('report_dir', 'evidence/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = report_dir / f"{event['target_id']}_closeout_{ts}.md"
    error_block = '\n'.join(f'- {error}' for error in errors) if errors else '- none'
    artifacts = bundle_data.get('required_artifacts', []) + bundle_data.get('supporting_artifacts', [])
    artifact_block = '\n'.join(f"- {item.get('path')} ({item.get('kind')}, required={item.get('required')}, result={item.get('validation_result', 'n/a')})" for item in artifacts) or '- none'
    out.write_text(
        f"# CAT Closeout Report\n\n"
        f"Target: {event['target_type']} {event['target_id']}\n\n"
        f"Transition: {event['to_status']}\n\n"
        f"Allowed: {event['allowed']}\n\n"
        f"Dry Run: {event['dry_run']}\n\n"
        f"Reason: {event['reason']}\n\n"
        f"Message: {event['message']}\n\n"
        f"Evidence Bundle: {event['bundle']}\n\n"
        f"Validation Result: {bundle_data.get('validation_result')}\n\n"
        f"## Summary\n\n{bundle_data.get('summary')}\n\n"
        f"## Artifacts\n\n{artifact_block}\n\n"
        f"## Errors\n\n{error_block}\n\n"
        f"## Learning\n\n{bundle_data.get('learning_note')}\n\n"
        f"Created: {event['timestamp']}\n",
        encoding='utf-8',
    )
    return out


def append_closeout_event(event: dict[str, Any]) -> None:
    rules = load_rules()
    log_path = ROOT / rules.get('audit', {}).get('closeout_log', 'evidence/logs/closeouts.jsonl')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, sort_keys=True) + '\n')


def run_closeout(target_type: str, target_id: str, to_status: str, bundle: str, reason: str, actor: str, dry_run: bool, move: bool) -> tuple[int, dict[str, Any]]:
    bundle_path = Path(bundle)
    if not bundle_path.is_absolute():
        bundle_path = ROOT / bundle_path
    ok, errors, data = validate_bundle(bundle_path)

    id_matches = True
    if data.get('target_type') != target_type:
        errors.append(f"bundle target_type {data.get('target_type')} does not match requested {target_type}")
        id_matches = False
    if target_type == 'bead' and data.get('bead_id') != target_id:
        errors.append(f"bundle bead_id {data.get('bead_id')} does not match requested {target_id}")
        id_matches = False
    if target_type == 'mission' and data.get('mission_id') != target_id:
        errors.append(f"bundle mission_id {data.get('mission_id')} does not match requested {target_id}")
        id_matches = False
    ok = ok and id_matches

    event = {
        'timestamp': utc_now(),
        'target_type': target_type,
        'target_id': target_id,
        'to_status': to_status,
        'bundle': rel(bundle_path),
        'allowed': ok,
        'dry_run': dry_run,
        'reason': reason,
        'actor': actor,
        'message': 'closeout allowed' if ok else 'closeout blocked by evidence gate',
        'errors': errors,
        'transition_event': None,
    }

    report_path = write_closeout_report(event, data, errors)
    event['report'] = rel(report_path)

    if not ok:
        append_closeout_event(event)
        return 1, event

    transition_code, transition_event = apply_transition(
        target_type,
        target_id,
        to_status,
        reason,
        rel(bundle_path),
        actor,
        dry_run,
        move,
    )
    event['transition_event'] = transition_event
    if transition_code != 0:
        event['allowed'] = False
        event['message'] = f"closeout evidence passed but transition failed: {transition_event.get('message')}"
        append_closeout_event(event)
        return transition_code, event

    append_closeout_event(event)
    return 0, event


def print_event(event: dict[str, Any]) -> None:
    print('# CAT Closeout Result')
    print()
    print(f"Target: {event['target_type']} {event['target_id']}")
    print(f"To Status: {event['to_status']}")
    print(f"Allowed: {event['allowed']}")
    print(f"Dry Run: {event['dry_run']}")
    print(f"Message: {event['message']}")
    print(f"Bundle: {event['bundle']}")
    print(f"Report: {event.get('report')}")
    if event.get('errors'):
        print()
        print('## Errors')
        for error in event['errors']:
            print(f'- {error}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate evidence and close out CAT missions or BEADs.')
    parser.add_argument('--type', required=True, choices=['mission', 'bead'], dest='target_type')
    parser.add_argument('--id', required=True, dest='target_id')
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--to', required=True, dest='to_status')
    parser.add_argument('--reason', required=True)
    parser.add_argument('--actor', default='Human Owner')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--move', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    code, event = run_closeout(args.target_type, args.target_id, args.to_status, args.bundle, args.reason, args.actor, args.dry_run, args.move)
    if args.json:
        print(json.dumps(event, indent=2, sort_keys=True))
    else:
        print_event(event)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
