#!/usr/bin/env python3
"""cat_render_sprint_state.py — auto-generate SPRINT_STATE.md and AGENT_HANDOFF_QUEUE.md."""
from __future__ import annotations

import argparse
from pathlib import Path

from cat_align_common import beads_for_mission
from common import ROOT, load_yaml, rel, utc_now

BANNER = '<!-- AUTO-GENERATED — do not edit manually. Run cat_render_sprint_state.py or cat_transition.py -->'


def _queued_beads(mission_id: str, root: Path) -> list[dict]:
    beads = []
    for bid, status, path in beads_for_mission(mission_id, root):
        if status in {'queued', 'active'}:
            data = load_yaml(path)
            beads.append({
                'bead_id': bid,
                'status': status,
                'title': data.get('title', ''),
                'agent_role': data.get('agent_role', ''),
            })
    beads.sort(key=lambda b: b['bead_id'])
    return beads


def render_sprint_state(root: Path = ROOT) -> str:
    tower = load_yaml(root / 'state/TOWER_STATE.yaml')
    registry = load_yaml(root / 'missions/registry/MISSION_REGISTRY.yaml')
    active_mission_id = tower.get('active_mission_id') or registry.get('active_mission_id') or ''
    active_bead_id = tower.get('active_bead_id') or ''
    active_entry = next(
        (m for m in registry.get('missions', []) if m.get('mission_id') == active_mission_id),
        None,
    )

    lines = [
        BANNER,
        '',
        '# CAT Sprint State',
        '',
        f'_Generated: {utc_now()}_',
        '',
        '| Field | Value |',
        '|---|---|',
        f"| Active Sprint | {tower.get('active_sprint', '—')} |",
        f"| Tower Status | {tower.get('status', '—')} |",
        f"| Active Mission | {active_mission_id or '—'} |",
        f"| Active BEAD | {active_bead_id or '—'} |",
        f"| Mission Status | {active_entry.get('status') if active_entry else '—'} |",
        f"| GO Mode | {tower.get('go_mode', '—')} |",
        f"| Sprint Goal | {tower.get('sprint_goal', '—')} |",
        '',
        '## Canonical Sources',
        '',
        '- `state/TOWER_STATE.yaml` — operator control plane',
        '- `missions/registry/MISSION_REGISTRY.yaml` — mission index',
        '- This file is generated; edit tower/registry, not this file.',
        '',
    ]
    return '\n'.join(lines)


def render_handoff_queue(root: Path = ROOT) -> str:
    tower = load_yaml(root / 'state/TOWER_STATE.yaml')
    registry = load_yaml(root / 'missions/registry/MISSION_REGISTRY.yaml')
    active_mission_id = tower.get('active_mission_id') or registry.get('active_mission_id') or ''

    lines = [
        BANNER,
        '',
        '# Agent Handoff Queue',
        '',
        f'_Generated: {utc_now()}_',
        '',
    ]

    if not active_mission_id:
        lines.extend([
            '## Status',
            '',
            'No active mission — tower is in post-sprint idle or awaiting kickoff.',
            '',
        ])
        return '\n'.join(lines)

    beads = _queued_beads(active_mission_id, root)
    active = [b for b in beads if b['status'] == 'active']
    queued = [b for b in beads if b['status'] == 'queued']

    if active:
        lines.append('## Active')
        lines.append('')
        for b in active:
            lines.extend([
                f"### {b['bead_id']} — {b['title']}",
                '',
                f"- Agent Role: {b['agent_role']}",
                f"- Mission: {active_mission_id}",
                '',
            ])

    if queued:
        lines.append('## Next')
        lines.append('')
        for b in queued:
            lines.extend([
                f"### {b['bead_id']} — {b['title']}",
                '',
                f"- Agent Role: {b['agent_role']}",
                f"- Status: queued",
                '',
            ])

    if not active and not queued:
        lines.extend([
            '## Status',
            '',
            f'Mission {active_mission_id} has no queued or active BEADs.',
            '',
        ])

    return '\n'.join(lines)


def write_sprint_state(root: Path = ROOT) -> None:
    sprint_path = root / 'state/SPRINT_STATE.md'
    handoff_path = root / 'state/AGENT_HANDOFF_QUEUE.md'
    sprint_path.write_text(render_sprint_state(root) + '\n', encoding='utf-8')
    handoff_path.write_text(render_handoff_queue(root) + '\n', encoding='utf-8')
    print(f'Wrote {rel(sprint_path)}')
    print(f'Wrote {rel(handoff_path)}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Render sprint state markdown from tower/registry.')
    args = parser.parse_args()
    write_sprint_state()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
