#!/usr/bin/env python3
"""CAT Agent Scorecard Mutation.

Records agent execution quality events into agents/registry/AGENT_SCORECARD.yaml
and writes per-bead entries to agents/scorecards/.

Fields per event:
  agent_role, mission_id, bead_id, result (bead_completed|bead_failed|incident),
  validation_passed, budget_used, incident_count, updated_at

Modes:
  --dry-run --sample     Print a sample mutation without writing anything
  --dry-run              With --role/--bead-id/--event: print what would change
  --record               Actually mutate AGENT_SCORECARD.yaml and write scorecard
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCORECARD_PATH = ROOT / 'agents' / 'registry' / 'AGENT_SCORECARD.yaml'
SCORECARDS_DIR = ROOT / 'agents' / 'scorecards'

DELTA_MAP = {
    'bead_completed': 5,
    'bead_failed': -10,
    'incident': -15,
    'promotion': 0,
    'demotion': 0,
}

SCORE_FLOOR = 0
SCORE_CAP = 100

SAMPLE_EVENT = {
    'agent_role': 'Builder',
    'mission_id': 'MP-CAT-A014-4C01',
    'bead_id': 'BEAD-CAT-A014-4C01-06',
    'result': 'bead_completed',
    'validation_passed': True,
    'budget_used': 3,
    'incident_count': 0,
}


def _load_scorecard() -> dict[str, Any]:
    return yaml.safe_load(SCORECARD_PATH.read_text(encoding='utf-8')) or {}


def _find_agent(data: dict, role: str) -> dict[str, Any] | None:
    for agent in data.get('agents', []):
        if agent.get('role') == role:
            return agent
    return None


def compute_mutation(
    data: dict[str, Any],
    agent_role: str,
    bead_id: str,
    mission_id: str,
    result: str,
    validation_passed: bool = True,
    budget_used: int = 0,
    incident_count: int = 0,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Return a new scorecard dict with the mutation applied (does not write)."""
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc).isoformat()

    data = copy.deepcopy(data)
    agent = _find_agent(data, agent_role)
    if agent is None:
        agent = {
            'role': agent_role,
            'score': data.get('score_policy', {}).get('starting_score', 70),
            'completed_beads': 0,
            'failed_beads': 0,
            'incidents': 0,
            'current_trust': 'provisional',
            'history': [],
        }
        data.setdefault('agents', []).append(agent)

    delta = DELTA_MAP.get(result, 0)
    if result == 'bead_failed' and not validation_passed:
        delta -= 5
    if incident_count > 0:
        delta -= incident_count * 5

    new_score = max(SCORE_FLOOR, min(SCORE_CAP, agent['score'] + delta))
    agent['score'] = new_score

    if result == 'bead_completed':
        agent['completed_beads'] = agent.get('completed_beads', 0) + 1
    elif result == 'bead_failed':
        agent['failed_beads'] = agent.get('failed_beads', 0) + 1
    if result == 'incident' or incident_count > 0:
        agent['incidents'] = agent.get('incidents', 0) + (incident_count or 1)

    policy = data.get('score_policy', {})
    if new_score >= policy.get('promote_threshold', 85):
        agent['current_trust'] = 'trusted'
    elif new_score <= policy.get('demote_threshold', 55):
        agent['current_trust'] = 'restricted'

    history_entry: dict[str, Any] = {
        'timestamp': timestamp,
        'event': result,
        'delta': delta,
        'bead_id': bead_id,
    }
    if mission_id:
        history_entry['note'] = f"mission={mission_id}"
    agent.setdefault('history', []).append(history_entry)

    data['last_updated'] = timestamp
    return data


def format_scorecard_entry(
    agent_role: str,
    bead_id: str,
    mission_id: str,
    result: str,
    validation_passed: bool,
    budget_used: int,
    incident_count: int,
    timestamp: str,
) -> dict[str, Any]:
    return {
        'timestamp': timestamp,
        'event': result,
        'bead_id': bead_id,
        'role': agent_role,
        'mission_id': mission_id,
        'validation_passed': validation_passed,
        'budget_used': budget_used,
        'incident_count': incident_count,
        'updated_at': timestamp,
    }


def record_event(
    agent_role: str,
    bead_id: str,
    mission_id: str,
    result: str,
    validation_passed: bool = True,
    budget_used: int = 0,
    incident_count: int = 0,
    dry_run: bool = False,
) -> tuple[dict[str, Any], Path | None]:
    """Apply mutation. Returns (new_data, scorecard_path_or_None_if_dry_run)."""
    ts = datetime.now(tz=timezone.utc).isoformat()
    data = _load_scorecard()
    new_data = compute_mutation(
        data, agent_role, bead_id, mission_id, result,
        validation_passed, budget_used, incident_count, timestamp=ts,
    )
    entry = format_scorecard_entry(
        agent_role, bead_id, mission_id, result,
        validation_passed, budget_used, incident_count, ts,
    )
    entry_name = f"{bead_id}_{agent_role}_{result}.yaml"
    entry_path = SCORECARDS_DIR / entry_name

    if not dry_run:
        SCORECARD_PATH.write_text(
            yaml.dump(new_data, default_flow_style=False, allow_unicode=True),
            encoding='utf-8',
        )
        entry_path.write_text(
            yaml.dump(entry, default_flow_style=False, allow_unicode=True),
            encoding='utf-8',
        )
        return new_data, entry_path

    return new_data, None


def _print_diff(old_data: dict, new_data: dict, agent_role: str) -> None:
    old_agent = _find_agent(old_data, agent_role)
    new_agent = _find_agent(new_data, agent_role)
    old_score = old_agent['score'] if old_agent else '(new)'
    new_score = new_agent['score'] if new_agent else '(new)'
    trust = new_agent['current_trust'] if new_agent else 'provisional'
    print(f"  role: {agent_role}")
    print(f"  score: {old_score} -> {new_score}")
    print(f"  trust: {trust}")
    history = (new_agent or {}).get('history', [])
    if history:
        last = history[-1]
        print(f"  last event: {last.get('event')} delta={last.get('delta')} bead={last.get('bead_id')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CAT Agent Scorecard Mutation.")
    parser.add_argument('--dry-run', action='store_true',
                        help="Print mutation without writing files.")
    parser.add_argument('--sample', action='store_true',
                        help="Use built-in sample event (with --dry-run).")
    parser.add_argument('--record', action='store_true',
                        help="Execute the mutation (writes files).")
    parser.add_argument('--role', help="Agent role (e.g. Builder)")
    parser.add_argument('--bead-id', help="BEAD ID")
    parser.add_argument('--mission-id', default='', help="Mission ID")
    parser.add_argument('--event', choices=list(DELTA_MAP.keys()),
                        help="Event type")
    parser.add_argument('--validation-passed', action='store_true', default=True)
    parser.add_argument('--no-validation-passed', dest='validation_passed',
                        action='store_false')
    parser.add_argument('--budget-used', type=int, default=0)
    parser.add_argument('--incident-count', type=int, default=0)
    args = parser.parse_args()

    if args.sample:
        ev = SAMPLE_EVENT
        print(f"[DRY-RUN] Sample event: {ev}")
        data = _load_scorecard()
        new_data = compute_mutation(
            data,
            ev['agent_role'], ev['bead_id'], ev['mission_id'], ev['result'],
            ev['validation_passed'], ev['budget_used'], ev['incident_count'],
        )
        _print_diff(data, new_data, ev['agent_role'])
        print("[DRY-RUN] No files written.")
        return 0

    if args.dry_run:
        if not all([args.role, args.bead_id, args.event]):
            print("--dry-run requires --role, --bead-id, --event (or use --sample)")
            return 1
        data = _load_scorecard()
        new_data = compute_mutation(
            data, args.role, args.bead_id, args.mission_id or '', args.event,
            args.validation_passed, args.budget_used, args.incident_count,
        )
        print("[DRY-RUN] Mutation preview:")
        _print_diff(data, new_data, args.role)
        print("[DRY-RUN] No files written.")
        return 0

    if args.record:
        if not all([args.role, args.bead_id, args.event]):
            print("--record requires --role, --bead-id, --event")
            return 1
        new_data, path = record_event(
            args.role, args.bead_id, args.mission_id or '', args.event,
            args.validation_passed, args.budget_used, args.incident_count,
            dry_run=False,
        )
        agent = _find_agent(new_data, args.role)
        print(f"Recorded {args.event} for {args.role} on {args.bead_id}")
        print(f"  score: {agent['score']}  trust: {agent['current_trust']}")
        print(f"  scorecard: {path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
