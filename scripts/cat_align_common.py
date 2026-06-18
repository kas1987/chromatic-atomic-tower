#!/usr/bin/env python3
"""Shared helpers for mission/BEAD state alignment checks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from common import ROOT, load_yaml, rel

MISSION_TERMINAL = frozenset({'closed', 'learned', 'abandoned'})
BEAD_TERMINAL = frozenset({'completed', 'failed', 'archived'})
BEAD_ACTIVE_STATES = frozenset({'active', 'in_progress', 'validating', 'reviewed', 'changes_requested'})

MISSION_GLOB_PATTERNS = [
    'missions/registry/MISSION_REGISTRY.yaml',
    'missions/active/*.yaml',
    'missions/backlog/*.yaml',
    'missions/archived/*.yaml',
    'missions/examples/*.yaml',
]

BEAD_GLOB_PATTERNS = [
    'beads/active/*.yaml',
    'beads/completed/*.yaml',
    'beads/failed/*.yaml',
    'beads/examples/*.yaml',
]


@dataclass
class DriftItem:
    code: str
    message: str
    remediation: str = ''


@dataclass
class AlignmentResult:
    drift: list[DriftItem] = field(default_factory=list)
    ok: list[str] = field(default_factory=list)

    @property
    def is_aligned(self) -> bool:
        return not self.drift

    def report(self) -> str:
        lines = []
        for msg in self.ok:
            lines.append(f'OK    {msg}')
        for item in self.drift:
            line = f'DRIFT [{item.code}] {item.message}'
            if item.remediation:
                line += f' | fix: {item.remediation}'
            lines.append(line)
        if self.is_aligned:
            lines.append('State is ALIGNED — no drift detected.')
        else:
            lines.append(f'State is MISALIGNED — {len(self.drift)} drift(s) detected.')
        return '\n'.join(lines)


def normalize_bead_id(value: object) -> str:
    if value is None or value == '':
        return ''
    return str(value)


def normalize_mission_id(value: object) -> str:
    if value is None or value == '':
        return ''
    return str(value)


def find_bead_contract(bead_id: str, root: Path = ROOT) -> tuple[dict | None, Path | None, str | None]:
    """Return (data, path, folder_label) for a BEAD id across bead folders."""
    if not bead_id:
        return None, None, None
    for folder in ('active', 'completed', 'failed', 'examples'):
        for path in sorted((root / 'beads' / folder).glob('*.yaml')):
            data = load_yaml(path)
            if data and data.get('bead_id') == bead_id:
                return data, path, folder
    return None, None, None


def find_mission_contract(mission_id: str, root: Path = ROOT) -> tuple[dict | None, Path | None]:
    if not mission_id:
        return None, None
    for pattern in ['missions/active/*.yaml', 'missions/backlog/*.yaml', 'missions/archived/*.yaml']:
        for path in sorted(root.glob(pattern)):
            data = load_yaml(path)
            if data and data.get('mission_id') == mission_id:
                return data, path
    return None, None


CONTRACT_MISSION_PATTERNS = [
    'missions/active/*.yaml',
    'missions/backlog/*.yaml',
    'missions/archived/*.yaml',
    'missions/examples/*.yaml',
]


def list_mission_contract_paths(root: Path = ROOT) -> dict[str, list[str]]:
    """Map mission_id -> contract file paths (collision when 2+ paths)."""
    ids: dict[str, list[str]] = {}
    for pattern in CONTRACT_MISSION_PATTERNS:
        for path in sorted(root.glob(pattern)):
            data = load_yaml(path)
            if not data:
                continue
            mid = data.get('mission_id')
            if mid:
                ids.setdefault(mid, []).append(rel(path))
    return ids


def list_mission_ids(root: Path = ROOT) -> dict[str, list[str]]:
    """Backward-compatible alias — contract paths only."""
    return list_mission_contract_paths(root)


def mission_contract_collisions(root: Path = ROOT) -> list[dict]:
    """Return collisions where the same mission_id appears in 2+ contract files."""
    collisions = []
    for mid, sources in sorted(list_mission_contract_paths(root).items()):
        unique = sorted(set(sources))
        if len(unique) > 1:
            collisions.append({'mission_id': mid, 'sources': unique})
    return collisions


def list_bead_ids(root: Path = ROOT) -> dict[str, list[str]]:
    ids: dict[str, list[str]] = {}
    for pattern in BEAD_GLOB_PATTERNS:
        for path in sorted(root.glob(pattern)):
            data = load_yaml(path)
            if not data:
                continue
            bid = data.get('bead_id')
            if bid:
                ids.setdefault(bid, []).append(rel(path))
    return ids


def beads_for_mission(mission_id: str, root: Path = ROOT) -> list[tuple[str, str, Path]]:
    """Return (bead_id, status, path) for all BEADs belonging to mission_id."""
    found: list[tuple[str, str, Path]] = []
    for pattern in BEAD_GLOB_PATTERNS:
        for path in sorted(root.glob(pattern)):
            data = load_yaml(path)
            if data and data.get('mission_id') == mission_id:
                found.append((data.get('bead_id', ''), data.get('status', ''), path))
    return found


def is_post_sprint_idle(tower: dict) -> bool:
    return tower.get('status') in {'sprint_idle', 'post_sprint_idle'}
