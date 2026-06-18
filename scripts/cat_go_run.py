#!/usr/bin/env python3
"""cat_go_run.py — ACTIVE GO-mode orchestrator (G-1a).

Builds on the read-only spine ``cat_go.py`` (which it imports) to advance a
mission stage-by-stage.  Default is **dry-run** — nothing is mutated.  Pass
``--execute`` to trigger automatable actions via audited sub-scripts only.

SAFETY RULES
- Default: dry-run; mutate NOTHING.
- --execute: only proceeds when plan_action() says automatable=True AND the
  human-gate confirmation check has been acknowledged.
- Never writes tower/registry/BEAD state directly — only via subprocess call
  to cat_sprint_closeout.py.

Usage:
    python scripts/cat_go_run.py                         # dry-run, active mission
    python scripts/cat_go_run.py --mission MP-CAT-A011-4C01
    python scripts/cat_go_run.py --json
    python scripts/cat_go_run.py --execute --confirm     # human gate ack via flag
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Pull the spine in — never reimplement its stage logic.
from cat_go import STAGES, _active_mission_id, evaluate
from common import ROOT, rel, utc_now

EVIDENCE_DIR = ROOT / 'evidence' / 'go'


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def next_actionable_stage(record: dict) -> str | None:
    """Return the first stage in STAGES whose status is 'pending', else None."""
    stages = record.get('stages', {})
    for stage in STAGES:
        if stages.get(stage, {}).get('status') == 'pending':
            return stage
    return None


def plan_action(record: dict) -> dict:
    """Return a plan dict: {next_stage, action, automatable, reason}.

    Decision matrix:
    - No pending stage          -> action='none', automatable=False
    - next_stage=='continue_close' and conditions met
                                -> action='run cat_sprint_closeout.py', automatable=True
    - Any other pending stage   -> action='manual: ...', automatable=False
    """
    next_stage = next_actionable_stage(record)

    if next_stage is None:
        return {
            'next_stage': None,
            'action': 'none',
            'automatable': False,
            'reason': 'all stages satisfied',
        }

    if next_stage == 'continue_close':
        # Automatable when: bead_count > 0 AND every stage except continue_close
        # is satisfied (or na) AND either the detail mentions 'ready to close'
        # or all other stages are fully satisfied.
        bead_count = record.get('bead_count', 0)
        other_stages_ok = all(
            record.get('stages', {}).get(s, {}).get('status') in ('satisfied', 'na')
            for s in STAGES
            if s != 'continue_close'
        )
        detail = record.get('stages', {}).get('continue_close', {}).get('detail', '')
        ready_hint = 'ready to close' in detail.lower()

        if bead_count > 0 and (other_stages_ok or ready_hint):
            return {
                'next_stage': 'continue_close',
                'action': 'run cat_sprint_closeout.py',
                'automatable': True,
                'reason': (
                    f'all BEADs terminal and other stages satisfied '
                    f'({bead_count} BEAD(s)); mission ready to close'
                ),
            }

    # Fallthrough: stage is agent/operator-driven or preconditions not met.
    return {
        'next_stage': next_stage,
        'action': f'manual: {next_stage} is agent/operator-driven',
        'automatable': False,
        'reason': f'stage {next_stage} requires agent or operator action before automation',
    }


# ---------------------------------------------------------------------------
# Human gate
# ---------------------------------------------------------------------------

def _human_gate_close(mission_id: str, actor: str, *, confirmed: bool) -> bool:
    """Flag-based human gate (no interactive prompt — safe under CI/automation).

    The gate is acknowledged out-of-band by passing ``--confirm``; without it,
    ``--execute`` prints the notice and refuses. This keeps "No Gate = No
    Promotion" enforceable without an ``input()`` call that would hang in a
    non-interactive shell.
    """
    print()
    print('=' * 70)
    print('  HUMAN GATE — Mission Closeout Requires Human Owner Approval')
    print('=' * 70)
    print(f'  Mission : {mission_id}')
    print(f'  Actor   : {actor}')
    print('  Action  : invoke cat_sprint_closeout.py --execute')
    print()
    print('  This will permanently close the mission, archive all BEADs,')
    print('  update the registry, and set the tower to sprint_idle.')
    print()
    if confirmed:
        print('  Confirmed via --confirm.')
        return True
    print('  Refused: re-run with --execute --confirm to proceed.')
    return False


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Active GO-mode orchestrator — advances a mission stage by stage.',
    )
    parser.add_argument(
        '--mission',
        default='',
        help='Mission ID (default: active mission from tower)',
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--dry-run',
        dest='dry_run',
        action='store_true',
        default=True,
        help='Dry-run mode (default): inspect only, mutate nothing',
    )
    mode_group.add_argument(
        '--execute',
        dest='dry_run',
        action='store_false',
        help='Execute automatable actions (human gate required)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit the action record as JSON',
    )
    parser.add_argument(
        '--actor',
        default='Human Owner',
        help='Actor name for audit records (default: Human Owner)',
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Acknowledge the human gate for a mission-close --execute',
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    mission_id: str = (args.mission.strip() or _active_mission_id()).strip()

    # Evaluate current state via the spine.
    go_run_record = evaluate(mission_id)
    action_plan = plan_action(go_run_record)

    # Build the top-level emitted record.
    emit_record: dict = {
        'kind': 'go_run_action',
        'timestamp': utc_now(),
        'mission_id': mission_id or None,
        'dry_run': dry_run,
        'action': action_plan,
        'go_run_record': go_run_record,
    }

    # --json path (always): just print JSON and exit.
    if args.json:
        print(json.dumps(emit_record, indent=2))
        return 0

    # Human-readable output (always in non-json mode).
    _print_human(go_run_record, action_plan, dry_run=dry_run)

    # --execute path.
    if not dry_run:
        if not action_plan['automatable']:
            print()
            print(f'Not automatable. Recommended action: {action_plan["action"]}')
            return 0

        # Only automatable action currently: close via cat_sprint_closeout.py.
        if not _human_gate_close(mission_id, args.actor, confirmed=args.confirm):
            return 1

        cmd = [
            sys.executable,
            str(ROOT / 'scripts' / 'cat_sprint_closeout.py'),
            '--execute',
            '--mission', mission_id,
            '--actor', args.actor,
        ]
        print(f'\nInvoking: {" ".join(cmd)}')
        result = subprocess.run(cmd, cwd=str(ROOT))

        # Write evidence only on --execute.
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        slug = (mission_id or 'idle').replace('/', '_')
        out_path = EVIDENCE_DIR / f'go_action_{slug}.json'
        out_path.write_text(json.dumps(emit_record, indent=2) + '\n', encoding='utf-8')
        print(f'\nwrote {rel(out_path)}')

        return result.returncode

    return 0


def _print_human(go_run_record: dict, action_plan: dict, *, dry_run: bool) -> None:
    _GLYPH = {'satisfied': '[x]', 'pending': '[ ]', 'na': '[-]'}
    mid = go_run_record.get('mission_id') or '(none — tower sprint_idle)'
    mode_label = '[DRY-RUN]' if dry_run else '[EXECUTE]'

    print(f'GO-run orchestrator {mode_label} — mission {mid}')
    print(
        f'  {go_run_record["stages_satisfied"]}/{go_run_record["stages_total"]} stages satisfied'
        f' · {go_run_record["bead_count"]} BEAD(s)'
        + (f' · mission {go_run_record["mission_status"]}' if go_run_record.get("mission_status") else '')
    )
    print()
    for i, name in enumerate(STAGES, 1):
        st = go_run_record['stages'][name]
        print(f'  {i}. {_GLYPH[st["status"]]} {name:<16} {st["detail"]}')

    print()
    automatable_label = 'YES' if action_plan['automatable'] else 'no'
    print(f'  Planned action  : {action_plan["action"]}')
    print(f'  Automatable     : {automatable_label}')
    print(f'  Reason          : {action_plan["reason"]}')


if __name__ == '__main__':
    sys.exit(main())
