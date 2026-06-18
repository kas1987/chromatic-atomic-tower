#!/usr/bin/env python3
"""Tests for cat_mission_id_check.py."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_mission_id_check import check_collisions, suggest_next_legacy_id


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


def test_no_collision_clean_fixture(tmp_path):
    _write(tmp_path / 'missions/active/MP-TEST-001.yaml', {
        'mission_id': 'MP-TEST-001', 'title': 'One', 'status': 'draft',
    })
    mission_c, bead_c = check_collisions(tmp_path)
    assert mission_c == []
    assert bead_c == []


def test_mission_collision_detected(tmp_path):
    _write(tmp_path / 'missions/active/MP-DUP-001.yaml', {
        'mission_id': 'MP-DUP-001', 'title': 'A', 'status': 'draft',
    })
    _write(tmp_path / 'missions/backlog/MP-DUP-001_COPY.yaml', {
        'mission_id': 'MP-DUP-001', 'title': 'B', 'status': 'draft',
    })
    mission_c, _ = check_collisions(tmp_path)
    assert len(mission_c) == 1
    assert mission_c[0]['mission_id'] == 'MP-DUP-001'
    assert len(mission_c[0]['sources']) == 2


def test_suggest_next_legacy_id(tmp_path):
    _write(tmp_path / 'missions/active/MP-CAT-005.yaml', {
        'mission_id': 'MP-CAT-005', 'title': 'Five', 'status': 'closed',
    })
    suggested = suggest_next_legacy_id(tmp_path)
    assert suggested == 'MP-CAT-006'
