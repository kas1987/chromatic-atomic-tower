#!/usr/bin/env python3
"""cat_agent_scorecard.py — CLI scoring engine for CAT agent trust scorecards.

Subcommands:
  score-bead  --role ROLE --bead BEAD_ID --result {completed,failed}
  penalize    --role ROLE --bead BEAD_ID [--note TEXT]
  promote     --role ROLE --bead BEAD_ID [--note TEXT]
  demote      --role ROLE --bead BEAD_ID [--note TEXT]
  report      [--role ROLE]

Default mode: dry-run (prints proposed changes, writes nothing).
Pass --execute to write changes to AGENT_SCORECARD.yaml.

Scoring formula:
  bead_completed: +5
  bead_failed:   -10
  incident:      -15  (floor: severe_incident_cap, default 40)
  promote:       trust → trusted   (score must be >= promote_threshold)
  demote:        trust → restricted (score must be <= demote_threshold)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCORECARD_PATH = ROOT / 'agents/registry/AGENT_SCORECARD.yaml'

SCORE_DELTA = {
    'bead_completed': 5,
    'bead_failed': -10,
    'incident': -15,
}


def _load_scorecard() -> dict:
    try:
        data = yaml.safe_load(SCORECARD_PATH.read_text(encoding='utf-8')) or {}
    except FileNotFoundError:
        print(f'error: scorecard not found at {SCORECARD_PATH}', file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f'error: invalid YAML in scorecard: {exc}', file=sys.stderr)
        sys.exit(1)
    return data


def _save_scorecard(data: dict) -> None:
    SCORECARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORECARD_PATH.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=False)


def _find_agent(agents: list, role: str) -> dict | None:
    for agent in agents:
        if (agent.get('role') or '').lower() == role.lower():
            return agent
    return None


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clamp_score(score: float, floor: float) -> float:
    return max(floor, min(100.0, score))


def cmd_score_bead(args: argparse.Namespace) -> int:
    data = _load_scorecard()
    policy = data.get('score_policy') or {}
    floor = policy.get('severe_incident_cap', 40)
    agents = data.get('agents') or []

    agent = _find_agent(agents, args.role)
    if agent is None:
        print(f'error: role {args.role!r} not found in scorecard', file=sys.stderr)
        return 1

    event = 'bead_completed' if args.result == 'completed' else 'bead_failed'
    delta = SCORE_DELTA[event]
    old_score = agent.get('score', 0)
    new_score = _clamp_score(old_score + delta, floor)

    print(f'score-bead [{args.role}] {event}: {old_score} -> {new_score} (delta {delta:+})')
    if args.dry_run:
        print('dry-run: no changes written')
        return 0

    agent['score'] = new_score
    if event == 'bead_completed':
        agent['completed_beads'] = agent.get('completed_beads', 0) + 1
    else:
        agent['failed_beads'] = agent.get('failed_beads', 0) + 1

    history_entry = {
        'timestamp': _utc_now(),
        'event': event,
        'delta': delta,
        'bead_id': args.bead,
    }
    agent.setdefault('history', []).append(history_entry)
    data['last_updated'] = _utc_now()
    _save_scorecard(data)

    increment_path = ROOT / 'agents/scorecards' / f'{args.bead}_{args.role}_{event}.yaml'
    increment_path.parent.mkdir(parents=True, exist_ok=True)
    with increment_path.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(history_entry | {'role': args.role}, fh, sort_keys=False)

    print(f'wrote {increment_path.relative_to(ROOT)}')
    return 0


def cmd_penalize(args: argparse.Namespace) -> int:
    data = _load_scorecard()
    policy = data.get('score_policy') or {}
    floor = policy.get('severe_incident_cap', 40)
    agents = data.get('agents') or []

    agent = _find_agent(agents, args.role)
    if agent is None:
        print(f'error: role {args.role!r} not found in scorecard', file=sys.stderr)
        return 1

    delta = SCORE_DELTA['incident']
    old_score = agent.get('score', 0)
    new_score = _clamp_score(old_score + delta, floor)

    print(f'penalize [{args.role}] incident: {old_score} -> {new_score} (delta {delta:+})')
    if args.dry_run:
        print('dry-run: no changes written')
        return 0

    agent['score'] = new_score
    agent['incidents'] = agent.get('incidents', 0) + 1
    history_entry: dict = {
        'timestamp': _utc_now(),
        'event': 'incident',
        'delta': delta,
        'bead_id': args.bead,
    }
    if getattr(args, 'note', None):
        history_entry['note'] = args.note
    agent.setdefault('history', []).append(history_entry)
    data['last_updated'] = _utc_now()
    _save_scorecard(data)
    print(f'incident penalty applied to {args.role}')
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    data = _load_scorecard()
    policy = data.get('score_policy') or {}
    promote_threshold = policy.get('promote_threshold', 85)
    agents = data.get('agents') or []

    agent = _find_agent(agents, args.role)
    if agent is None:
        print(f'error: role {args.role!r} not found in scorecard', file=sys.stderr)
        return 1

    score = agent.get('score', 0)
    if score < promote_threshold:
        print(
            f'error: {args.role} score {score} is below promote_threshold {promote_threshold}',
            file=sys.stderr,
        )
        return 1

    print(f'promote [{args.role}]: {agent.get("current_trust")} -> trusted (score={score})')
    if args.dry_run:
        print('dry-run: no changes written (human approval required before --execute)')
        return 0

    agent['current_trust'] = 'trusted'
    history_entry: dict = {
        'timestamp': _utc_now(),
        'event': 'promotion',
        'delta': 0,
        'bead_id': args.bead,
    }
    if getattr(args, 'note', None):
        history_entry['note'] = args.note
    agent.setdefault('history', []).append(history_entry)
    data['last_updated'] = _utc_now()
    _save_scorecard(data)
    print(f'{args.role} promoted to trusted')
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    data = _load_scorecard()
    policy = data.get('score_policy') or {}
    demote_threshold = policy.get('demote_threshold', 55)
    agents = data.get('agents') or []

    agent = _find_agent(agents, args.role)
    if agent is None:
        print(f'error: role {args.role!r} not found in scorecard', file=sys.stderr)
        return 1

    score = agent.get('score', 0)
    if score > demote_threshold:
        print(
            f'error: {args.role} score {score} is above demote_threshold {demote_threshold}',
            file=sys.stderr,
        )
        return 1

    print(f'demote [{args.role}]: {agent.get("current_trust")} -> restricted (score={score})')
    if args.dry_run:
        print('dry-run: no changes written (human approval required before --execute)')
        return 0

    agent['current_trust'] = 'restricted'
    history_entry: dict = {
        'timestamp': _utc_now(),
        'event': 'demotion',
        'delta': 0,
        'bead_id': args.bead,
    }
    if getattr(args, 'note', None):
        history_entry['note'] = args.note
    agent.setdefault('history', []).append(history_entry)
    data['last_updated'] = _utc_now()
    _save_scorecard(data)
    print(f'{args.role} demoted to restricted')
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = _load_scorecard()
    agents = data.get('agents') or []
    policy = data.get('score_policy') or {}

    if getattr(args, 'role', None):
        agents = [a for a in agents if (a.get('role') or '').lower() == args.role.lower()]
        if not agents:
            print(f'error: role {args.role!r} not found', file=sys.stderr)
            return 1

    rows = []
    for a in agents:
        rows.append({
            'role': a.get('role'),
            'score': a.get('score'),
            'trust': a.get('current_trust'),
            'completed_beads': a.get('completed_beads', 0),
            'failed_beads': a.get('failed_beads', 0),
            'incidents': a.get('incidents', 0),
            'history_entries': len(a.get('history') or []),
        })

    if getattr(args, 'json', False):
        print(json.dumps({'scorecard_version': data.get('version'), 'policy': policy, 'agents': rows}, indent=2))
    else:
        print(f'Agent Scorecard v{data.get("version", "?")} — {data.get("last_updated", "?")}')
        print(f'  promote>={policy.get("promote_threshold")} demote<={policy.get("demote_threshold")} floor={policy.get("severe_incident_cap")}')
        print()
        for r in rows:
            bar = '#' * int(r['score'] / 5)
            print(f'  {r["role"]:<14} score={r["score"]:>5.1f} [{bar:<20}] trust={r["trust"]}')
            print(f'               done={r["completed_beads"]} failed={r["failed_beads"]} incidents={r["incidents"]} history={r["history_entries"]}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='CAT agent trust scorecard CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', default=True, help='Print proposed changes (default)')
    mode.add_argument('--execute', dest='dry_run', action='store_false', help='Write changes to disk')

    sub = parser.add_subparsers(dest='command', required=True)

    p_score = sub.add_parser('score-bead', help='Record a BEAD outcome')
    p_score.add_argument('--role', required=True)
    p_score.add_argument('--bead', required=True)
    p_score.add_argument('--result', required=True, choices=['completed', 'failed'])

    p_pen = sub.add_parser('penalize', help='Apply incident penalty')
    p_pen.add_argument('--role', required=True)
    p_pen.add_argument('--bead', required=True)
    p_pen.add_argument('--note', default='')

    p_pro = sub.add_parser('promote', help='Promote agent to trusted')
    p_pro.add_argument('--role', required=True)
    p_pro.add_argument('--bead', required=True, help='BEAD ID triggering the review')
    p_pro.add_argument('--note', default='')

    p_dem = sub.add_parser('demote', help='Demote agent to restricted')
    p_dem.add_argument('--role', required=True)
    p_dem.add_argument('--bead', required=True, help='BEAD ID triggering the review')
    p_dem.add_argument('--note', default='')

    p_rep = sub.add_parser('report', help='Print scorecard summary')
    p_rep.add_argument('--role', default='')
    p_rep.add_argument('--json', action='store_true')

    args = parser.parse_args()
    dispatch = {
        'score-bead': cmd_score_bead,
        'penalize': cmd_penalize,
        'promote': cmd_promote,
        'demote': cmd_demote,
        'report': cmd_report,
    }
    return dispatch[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
