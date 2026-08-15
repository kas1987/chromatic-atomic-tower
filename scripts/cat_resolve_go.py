#!/usr/bin/env python3
"""Resolve CAT GO from official Beads into a validated Wisker dispatch."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cat_beads import (
    BeadsCommandError,
    bead_digest,
    build_wisker,
    claim_bead,
    ready_beads,
    select_ready,
    show_bead,
    write_packet,
)
from cat_state_freshness import check_alignment
from cat_align_common import normalize_bead_id
from common import ROOT, load_yaml, rel

ALLOWED_MISSION_STATUSES = {'approved', 'dispatched', 'in_progress', 'validating'}


def load_active_beads() -> list[dict]:
    """Deprecated compatibility shim; active CAT YAML no longer exists."""
    return []


def select_mission(registry: dict) -> dict | None:
    candidates = [m for m in registry.get('missions', []) if m.get('status') in ALLOWED_MISSION_STATUSES]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda m: (
            int(m.get('priority', 5)),
            -int(m.get('confidence', 0)),
            str(m.get('risk_level', 'critical')),
            str(m.get('created', '9999-99-99')),
            str(m.get('mission_id', '')),
        ),
    )[0]


def confidence_band(score: int) -> str:
    if score >= 90:
        return 'very_high'
    if score >= 75:
        return 'high'
    if score >= 60:
        return 'medium'
    if score >= 40:
        return 'low'
    return 'blocked'


def select_bead(mission: dict, beads: list[dict], *, allow_queued: bool = False) -> dict | None:
    """Pure compatibility selector for callers that already have issue data.

    It does not read CAT YAML. Production GO uses ``bd ready --json`` and
    ``select_ready`` from ``cat_beads``.
    """
    mission_id = mission.get('mission_id')
    allowed = {'open', 'in_progress'} | ({'queued'} if allow_queued else set())
    candidates = [b for b in beads if b.get('mission_id') == mission_id and b.get('status') in allowed]
    return sorted(candidates, key=lambda b: (int(b.get('priority', 5)), str(b.get('id', b.get('bead_id', '')))))[0] if candidates else None


def build_dispatch(mission: dict, bead: dict, wisker: dict | None = None, packet_path: Path | None = None) -> dict:
    if wisker is None:
        # Compatibility adapter for historical unit fixtures; this path is not
        # used by GO and never writes or reads the archived YAML store.
        digest = '0' * 64
        wisker = {
            'wisker_id': f'WISKER-{bead.get("id", bead.get("bead_id", "legacy"))}-00000000',
            'bd_id': bead.get('id', bead.get('bead_id', 'legacy')),
            'source_bead_digest': digest,
            'source_commit_sha': '0' * 40,
            'mission_id': bead.get('mission_id', mission.get('mission_id', '')),
            'title': bead.get('title', ''),
            'agent_role': bead.get('agent_role', 'Builder'),
            'autonomy_level': bead.get('autonomy_level', 'L1'),
            'confidence': bead.get('confidence', {'current': 0, 'minimum': 0}),
            'risk': {'level': bead.get('risk_level', 'medium'), 'reversibility': bead.get('reversibility', 'reversible')},
            'allowed_paths': bead.get('allowed_paths', []),
            'forbidden_paths': bead.get('forbidden_paths', []),
            'tool_budget': bead.get('tool_budget', {}),
            'definition_of_done': bead.get('definition_of_done', []),
            'validation': bead.get('validation', []),
            'stop_conditions': bead.get('stop_conditions', []),
            'required_output': bead.get('required_output', []),
        }
    packet_path = packet_path or Path('wiskers/packets') / f'{wisker["wisker_id"]}.yaml'
    confidence = wisker['confidence']
    score = int(confidence['current'])
    minimum = int(confidence['minimum'])
    blocked = score < minimum
    return {
        'dispatch_status': 'blocked' if blocked else 'ready',
        'reason': 'confidence below minimum' if blocked else 'official Beads selection produced a validated Wisker',
        'mission_id': wisker.get('mission_id') or mission.get('mission_id'),
        'mission_title': mission.get('title', wisker.get('mission_id', '')),
        'mission_level': mission.get('level', 'M1'),
        'mission_risk': mission.get('risk_level', wisker['risk']['level']),
        'bead_id': bead.get('id'),
        'bead_title': wisker.get('title', bead.get('title', '')),
        'bead_status': bead.get('status'),
        'wisker_id': wisker['wisker_id'],
        'wisker_path': rel(packet_path),
        'source_bead_digest': wisker['source_bead_digest'],
        'source_commit_sha': wisker['source_commit_sha'],
        'agent_role': wisker['agent_role'],
        'autonomy_level': wisker['autonomy_level'],
        'confidence': score,
        'confidence_minimum': minimum,
        'confidence_band': confidence_band(score),
        'risk_level': wisker['risk']['level'],
        'reversibility': wisker['risk']['reversibility'],
        'allowed_paths': wisker['allowed_paths'],
        'forbidden_paths': wisker['forbidden_paths'],
        'tool_budget': wisker['tool_budget'],
        'definition_of_done': wisker['definition_of_done'],
        'validation': wisker['validation'],
        'stop_conditions': wisker['stop_conditions'],
        'required_output': wisker['required_output'],
        'bead_path': None,
        'mission_path': mission.get('path'),
    }


def print_markdown(dispatch: dict) -> None:
    print('# CAT GO Dispatch Packet')
    print()
    print(f"Status: {dispatch['dispatch_status']}")
    print(f"Reason: {dispatch['reason']}")
    print()
    print(f"Mission: {dispatch['mission_id']} - {dispatch['mission_title']}")
    print(f"Official Bead: {dispatch['bead_id']} - {dispatch['bead_title']} ({dispatch['bead_status']})")
    print(f"Wisker: {dispatch['wisker_id']} ({dispatch['wisker_path']})")
    print(f"Agent Role: {dispatch['agent_role']}")
    print(f"Autonomy: {dispatch['autonomy_level']}")
    print(f"Confidence: {dispatch['confidence']} / minimum {dispatch['confidence_minimum']} ({dispatch['confidence_band']})")
    print(f"Risk: {dispatch['risk_level']}")
    print(f"Source Bead Digest: {dispatch['source_bead_digest']}")
    print(f"Source Commit: {dispatch['source_commit_sha']}")
    print()
    print('## Allowed Paths')
    for item in dispatch['allowed_paths']:
        print(f'- {item}')
    print()
    print('## Forbidden Paths')
    for item in dispatch['forbidden_paths']:
        print(f'- {item}')
    print()
    print('## Tool Budget')
    for key, value in dispatch['tool_budget'].items():
        print(f'- {key}: {value}')
    print()
    print('## Definition of Done')
    for item in dispatch['definition_of_done']:
        print(f'- {item}')
    print()
    print('## Validation')
    for item in dispatch['validation']:
        print(f"- {item.get('type')}: `{item.get('command')}` -> {item.get('evidence_path')}")
    print()
    print('## Stop Conditions')
    for item in dispatch['stop_conditions']:
        print(f'- {item}')


def _git_head() -> str:
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd=ROOT, timeout=5)
        sha = result.stdout.strip()
        return sha if len(sha) == 40 else '0' * 40
    except Exception:
        return '0' * 40


def _append_go_decision(allowed: bool, reason: str | None = None, sprint: str = '', bead_id: str = '', drifts: list[str] | None = None) -> None:
    log_path = ROOT / 'evidence' / 'logs' / 'go_decisions.jsonl'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'allowed': allowed,
        'reason': reason or ('alignment drift' if drifts else ''),
        'drifts': drifts or [],
        'sprint': sprint,
        'bead_id': bead_id,
        'commit_sha': _git_head(),
    }
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')


def _run_loghouse_self(strict: bool) -> int:
    cmd = [sys.executable, str(ROOT / 'scripts' / 'cat_loghouse.py'), '--mode', 'self']
    if strict:
        cmd.append('--strict')
    return subprocess.run(cmd, cwd=ROOT).returncode


def _validate_schema(instance: dict, schema_name: str) -> list[str]:
    try:
        import jsonschema
        schema = json.loads((ROOT / 'schemas' / schema_name).read_text(encoding='utf-8'))
        return [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(instance)]
    except ImportError:
        return ['jsonschema not installed — cannot validate schema']
    except Exception as exc:
        return [f'schema validation error: {exc}']


def _validate_against_schema(dispatch: dict) -> list[str]:
    """Backward-compatible name for the dispatch schema check."""
    return _validate_schema(dispatch, 'go_dispatch_packet.schema.json')


def _empty_queue_or_fail(tower: dict, issues: list[dict], sprint: str) -> int | None:
    if tower.get('active_mission_id'):
        return None
    if tower.get('status') == 'sprint_idle':
        _append_go_decision(True, 'idle CAT baseline; no approved mission selected', sprint)
        print(f'No approved mission available (sprint_idle — {len(issues)} official ready Bead(s) remain unassigned).')
        return 0
    _append_go_decision(False, 'no approved mission available', sprint)
    print('No approved mission available.')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Resolve CAT GO from official Beads into a Wisker dispatch packet.')
    parser.add_argument('--json', action='store_true', help='Print JSON instead of Markdown.')
    parser.add_argument('--format', choices=['json', 'markdown'], default=None)
    parser.add_argument('--check-schema', action='store_true', help='Validate Wisker and dispatch schemas.')
    parser.add_argument('--skip-align-check', action='store_true', help='Skip alignment gate (operator only).')
    parser.add_argument('--skip-loghouse', action='store_true', help='Skip LOGHOUSE self-monitor (operator only).')
    args = parser.parse_args()
    if args.format == 'json':
        args.json = True
    if args.check_schema:
        args.skip_align_check = True
        args.skip_loghouse = True

    tower = load_yaml(ROOT / 'state/TOWER_STATE.yaml')
    sprint = tower.get('active_sprint', 'SPRINT-000')
    if not args.skip_align_check:
        alignment = check_alignment(ROOT)
        if not alignment.is_aligned:
            _append_go_decision(False, 'mission/Beads alignment failed', sprint)
            print('GO blocked: mission/Beads state misaligned.')
            print(alignment.report())
            print('\nRemediation: python scripts/cat_align_check.py --strict')
            return 1

    try:
        ready = ready_beads()
    except BeadsCommandError as exc:
        _append_go_decision(False, str(exc), sprint)
        print(f'GO blocked: {exc}')
        return 1

    idle_result = _empty_queue_or_fail(tower, ready, sprint)
    if idle_result is not None:
        return idle_result

    registry = load_yaml(ROOT / 'missions/registry/MISSION_REGISTRY.yaml')
    mission = select_mission(registry)
    if not mission:
        _append_go_decision(False, 'no approved mission available', sprint)
        print('No approved mission available.')
        return 1

    bead: dict | None = None
    try:
        bead = select_ready(ready, mission_id=mission.get('mission_id'))
        if not bead:
            raise BeadsCommandError(f'no ready official Bead is assigned to mission {mission.get("mission_id")}')
        selected = show_bead(str(bead['id']))
        source_sha = _git_head()
        if source_sha == '0' * 40:
            raise BeadsCommandError('source Git commit SHA is unavailable; dispatch refused')
        wisker = build_wisker(selected, source_sha)
        errors = _validate_schema(wisker, 'wisker.schema.json')
        if errors:
            raise BeadsCommandError(f'invalid Wisker: {"; ".join(errors)}')
        before_digest = wisker['source_bead_digest']
        claimed = claim_bead(str(selected['id']))
        after = show_bead(str(selected['id']))
        if bead_digest(after) != before_digest:
            raise BeadsCommandError('source Bead digest changed while claiming; dispatch refused')
        packet_path = write_packet(wisker)
        dispatch = build_dispatch(mission, claimed or after, wisker, packet_path)
    except BeadsCommandError as exc:
        _append_go_decision(False, str(exc), sprint, str(bead.get('id', '')) if bead else '')
        print(f'GO blocked: {exc}')
        return 1

    _append_go_decision(dispatch['dispatch_status'] == 'ready', dispatch['reason'], sprint, dispatch['bead_id'])
    if args.json:
        print(json.dumps(dispatch, indent=2))
    else:
        print_markdown(dispatch)

    if args.check_schema:
        errors = _validate_schema(dispatch, 'go_dispatch_packet.schema.json')
        if errors:
            print('\nSCHEMA FAIL:')
            for error in errors:
                print(f'  - {error}')
            return 1
        print('\nSCHEMA PASS: Wisker and dispatch packets validate')

    if dispatch['dispatch_status'] != 'ready':
        return 1
    if not args.skip_loghouse and _run_loghouse_self(strict=True) != 0:
        print('\nGO blocked: LOGHOUSE self-monitor detected critical governance findings.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
