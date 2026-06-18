"""Unit tests for cat_align_common.py — shared alignment helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from cat_align_common import (
    MISSION_TERMINAL,
    BEAD_TERMINAL,
    BEAD_ACTIVE_STATES,
    DriftItem,
    AlignmentResult,
    normalize_bead_id,
    normalize_mission_id,
    find_bead_contract,
    find_mission_contract,
    list_mission_contract_paths,
    list_mission_ids,
    mission_contract_collisions,
    list_bead_ids,
    beads_for_mission,
    is_post_sprint_idle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_mission_terminal_states_defined():
    assert 'closed' in MISSION_TERMINAL
    assert 'learned' in MISSION_TERMINAL
    assert 'abandoned' in MISSION_TERMINAL


def test_bead_terminal_states_defined():
    assert 'completed' in BEAD_TERMINAL
    assert 'failed' in BEAD_TERMINAL
    assert 'archived' in BEAD_TERMINAL


def test_bead_active_states_defined():
    assert 'active' in BEAD_ACTIVE_STATES
    assert 'in_progress' in BEAD_ACTIVE_STATES


def test_terminal_and_active_states_are_disjoint():
    overlap = BEAD_TERMINAL & BEAD_ACTIVE_STATES
    assert not overlap, f'Terminal and active bead states must not overlap: {overlap}'


# ---------------------------------------------------------------------------
# DriftItem and AlignmentResult dataclasses
# ---------------------------------------------------------------------------

def test_drift_item_construction():
    item = DriftItem(code='TEST_CODE', message='something drifted')
    assert item.code == 'TEST_CODE'
    assert item.message == 'something drifted'
    assert item.remediation == ''


def test_drift_item_with_remediation():
    item = DriftItem(code='FIX_ME', message='bad state', remediation='run script')
    assert item.remediation == 'run script'


def test_alignment_result_empty_is_aligned():
    result = AlignmentResult()
    assert result.is_aligned


def test_alignment_result_with_drift_is_not_aligned():
    result = AlignmentResult(drift=[DriftItem(code='X', message='drift')])
    assert not result.is_aligned


def test_alignment_result_report_aligned():
    result = AlignmentResult(ok=['mission OK', 'bead OK'])
    report = result.report()
    assert 'ALIGNED' in report
    assert 'MISALIGNED' not in report
    assert 'OK' in report


def test_alignment_result_report_misaligned():
    result = AlignmentResult(drift=[DriftItem(code='DRIFT_CODE', message='something wrong')])
    report = result.report()
    assert 'MISALIGNED' in report
    assert 'DRIFT_CODE' in report
    assert 'something wrong' in report


def test_alignment_result_report_shows_remediation():
    result = AlignmentResult(drift=[DriftItem(code='X', message='msg', remediation='do this')])
    report = result.report()
    assert 'do this' in report
    assert 'fix:' in report


def test_alignment_result_drift_count_in_report():
    drifts = [DriftItem(code=f'D{i}', message=f'drift {i}') for i in range(3)]
    result = AlignmentResult(drift=drifts)
    report = result.report()
    assert '3' in report


# ---------------------------------------------------------------------------
# normalize_bead_id / normalize_mission_id
# ---------------------------------------------------------------------------

def test_normalize_bead_id_normal_string():
    assert normalize_bead_id('BEAD-CAT-A006-4C01-01') == 'BEAD-CAT-A006-4C01-01'


def test_normalize_bead_id_none_returns_empty():
    assert normalize_bead_id(None) == ''


def test_normalize_bead_id_empty_string_returns_empty():
    assert normalize_bead_id('') == ''


def test_normalize_bead_id_integer_coerces_to_string():
    assert normalize_bead_id(42) == '42'


def test_normalize_mission_id_normal_string():
    assert normalize_mission_id('MP-CAT-A006-4C01') == 'MP-CAT-A006-4C01'


def test_normalize_mission_id_none_returns_empty():
    assert normalize_mission_id(None) == ''


def test_normalize_mission_id_empty_string_returns_empty():
    assert normalize_mission_id('') == ''


def test_normalize_mission_id_integer_coerces_to_string():
    assert normalize_mission_id(123) == '123'


# ---------------------------------------------------------------------------
# find_bead_contract
# ---------------------------------------------------------------------------

def test_find_bead_contract_found_in_active(tmp_path):
    _write(tmp_path / 'beads/active/BEAD-TEST-01.yaml', {
        'bead_id': 'BEAD-CAT-TEST-01',
        'mission_id': 'MP-CAT-TEST',
        'status': 'active',
    })
    data, path, folder = find_bead_contract('BEAD-CAT-TEST-01', root=tmp_path)
    assert data is not None
    assert data['bead_id'] == 'BEAD-CAT-TEST-01'
    assert folder == 'active'
    assert path is not None


def test_find_bead_contract_found_in_completed(tmp_path):
    _write(tmp_path / 'beads/completed/BEAD-DONE.yaml', {
        'bead_id': 'BEAD-CAT-DONE-01',
        'mission_id': 'MP-CAT-TEST',
        'status': 'completed',
    })
    data, path, folder = find_bead_contract('BEAD-CAT-DONE-01', root=tmp_path)
    assert data is not None
    assert folder == 'completed'


def test_find_bead_contract_not_found_returns_nones(tmp_path):
    (tmp_path / 'beads/active').mkdir(parents=True, exist_ok=True)
    data, path, folder = find_bead_contract('BEAD-NONEXISTENT', root=tmp_path)
    assert data is None
    assert path is None
    assert folder is None


def test_find_bead_contract_empty_id_returns_nones(tmp_path):
    data, path, folder = find_bead_contract('', root=tmp_path)
    assert data is None
    assert path is None
    assert folder is None


# ---------------------------------------------------------------------------
# find_mission_contract
# ---------------------------------------------------------------------------

def test_find_mission_contract_found_in_active(tmp_path):
    _write(tmp_path / 'missions/active/MP-TEST.yaml', {
        'mission_id': 'MP-CAT-TEST-FIND',
        'status': 'approved',
    })
    data, path = find_mission_contract('MP-CAT-TEST-FIND', root=tmp_path)
    assert data is not None
    assert data['mission_id'] == 'MP-CAT-TEST-FIND'
    assert path is not None


def test_find_mission_contract_found_in_backlog(tmp_path):
    _write(tmp_path / 'missions/backlog/MP-BACKLOG.yaml', {
        'mission_id': 'MP-CAT-BACKLOG-01',
        'status': 'draft',
    })
    data, path = find_mission_contract('MP-CAT-BACKLOG-01', root=tmp_path)
    assert data is not None
    assert data['mission_id'] == 'MP-CAT-BACKLOG-01'


def test_find_mission_contract_not_found_returns_nones(tmp_path):
    (tmp_path / 'missions/active').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'missions/backlog').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'missions/archived').mkdir(parents=True, exist_ok=True)
    data, path = find_mission_contract('MP-CAT-DOES-NOT-EXIST', root=tmp_path)
    assert data is None
    assert path is None


def test_find_mission_contract_empty_id_returns_nones(tmp_path):
    data, path = find_mission_contract('', root=tmp_path)
    assert data is None
    assert path is None


# ---------------------------------------------------------------------------
# list_mission_contract_paths / list_mission_ids
# ---------------------------------------------------------------------------

def test_list_mission_contract_paths_single(tmp_path):
    _write(tmp_path / 'missions/active/MP-SINGLE.yaml', {
        'mission_id': 'MP-CAT-SINGLE-01',
        'status': 'approved',
    })
    result = list_mission_contract_paths(root=tmp_path)
    assert 'MP-CAT-SINGLE-01' in result
    assert len(result['MP-CAT-SINGLE-01']) == 1


def test_list_mission_contract_paths_empty_root(tmp_path):
    for d in ['missions/active', 'missions/backlog', 'missions/archived', 'missions/examples']:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    result = list_mission_contract_paths(root=tmp_path)
    assert result == {}


def test_list_mission_ids_is_alias(tmp_path):
    _write(tmp_path / 'missions/active/MP-ALIAS.yaml', {
        'mission_id': 'MP-CAT-ALIAS-01',
        'status': 'approved',
    })
    by_path = list_mission_contract_paths(root=tmp_path)
    by_ids = list_mission_ids(root=tmp_path)
    assert by_path == by_ids


# ---------------------------------------------------------------------------
# mission_contract_collisions
# ---------------------------------------------------------------------------

def test_mission_contract_collisions_none_when_unique(tmp_path):
    _write(tmp_path / 'missions/active/MP-A.yaml', {'mission_id': 'MP-CAT-A-01', 'status': 'approved'})
    _write(tmp_path / 'missions/active/MP-B.yaml', {'mission_id': 'MP-CAT-B-01', 'status': 'approved'})
    collisions = mission_contract_collisions(root=tmp_path)
    assert collisions == []


def test_mission_contract_collisions_detected(tmp_path):
    _write(tmp_path / 'missions/active/MP-DUP.yaml', {
        'mission_id': 'MP-CAT-DUP-01',
        'status': 'approved',
    })
    _write(tmp_path / 'missions/backlog/MP-DUP-COPY.yaml', {
        'mission_id': 'MP-CAT-DUP-01',
        'status': 'draft',
    })
    collisions = mission_contract_collisions(root=tmp_path)
    assert len(collisions) == 1
    assert collisions[0]['mission_id'] == 'MP-CAT-DUP-01'
    assert len(collisions[0]['sources']) >= 2


def test_mission_contract_collisions_empty_root(tmp_path):
    for d in ['missions/active', 'missions/backlog', 'missions/archived', 'missions/examples']:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    collisions = mission_contract_collisions(root=tmp_path)
    assert collisions == []


# ---------------------------------------------------------------------------
# list_bead_ids
# ---------------------------------------------------------------------------

def test_list_bead_ids_single(tmp_path):
    _write(tmp_path / 'beads/active/BEAD-01.yaml', {
        'bead_id': 'BEAD-CAT-A001-01',
        'mission_id': 'MP-CAT-A001',
    })
    result = list_bead_ids(root=tmp_path)
    assert 'BEAD-CAT-A001-01' in result


def test_list_bead_ids_empty_root(tmp_path):
    for d in ['beads/active', 'beads/completed', 'beads/failed', 'beads/examples']:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    result = list_bead_ids(root=tmp_path)
    assert result == {}


def test_list_bead_ids_collision_same_bead_two_files(tmp_path):
    _write(tmp_path / 'beads/active/BEAD-DUP.yaml', {
        'bead_id': 'BEAD-CAT-DUP-01',
        'mission_id': 'MP-CAT-TEST',
    })
    _write(tmp_path / 'beads/completed/BEAD-DUP-COPY.yaml', {
        'bead_id': 'BEAD-CAT-DUP-01',
        'mission_id': 'MP-CAT-TEST',
    })
    result = list_bead_ids(root=tmp_path)
    assert 'BEAD-CAT-DUP-01' in result
    assert len(result['BEAD-CAT-DUP-01']) == 2


# ---------------------------------------------------------------------------
# beads_for_mission
# ---------------------------------------------------------------------------

def test_beads_for_mission_returns_matching(tmp_path):
    _write(tmp_path / 'beads/active/B1.yaml', {
        'bead_id': 'BEAD-CAT-M01-01',
        'mission_id': 'MP-CAT-M01',
        'status': 'active',
    })
    _write(tmp_path / 'beads/active/B2.yaml', {
        'bead_id': 'BEAD-CAT-M01-02',
        'mission_id': 'MP-CAT-M01',
        'status': 'completed',
    })
    results = beads_for_mission('MP-CAT-M01', root=tmp_path)
    bead_ids = [r[0] for r in results]
    assert 'BEAD-CAT-M01-01' in bead_ids
    assert 'BEAD-CAT-M01-02' in bead_ids


def test_beads_for_mission_excludes_other_missions(tmp_path):
    _write(tmp_path / 'beads/active/B-OTHER.yaml', {
        'bead_id': 'BEAD-CAT-OTHER-01',
        'mission_id': 'MP-CAT-OTHER',
        'status': 'active',
    })
    results = beads_for_mission('MP-CAT-M01', root=tmp_path)
    assert results == []


def test_beads_for_mission_empty_returns_empty(tmp_path):
    for d in ['beads/active', 'beads/completed', 'beads/failed', 'beads/examples']:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    results = beads_for_mission('MP-CAT-GHOST', root=tmp_path)
    assert results == []


def test_beads_for_mission_result_shape(tmp_path):
    _write(tmp_path / 'beads/active/B1.yaml', {
        'bead_id': 'BEAD-CAT-SHAPE-01',
        'mission_id': 'MP-CAT-SHAPE',
        'status': 'active',
    })
    results = beads_for_mission('MP-CAT-SHAPE', root=tmp_path)
    assert len(results) == 1
    bead_id, status, path = results[0]
    assert bead_id == 'BEAD-CAT-SHAPE-01'
    assert status == 'active'
    assert isinstance(path, Path)


# ---------------------------------------------------------------------------
# is_post_sprint_idle
# ---------------------------------------------------------------------------

def test_is_post_sprint_idle_sprint_idle():
    assert is_post_sprint_idle({'status': 'sprint_idle'})


def test_is_post_sprint_idle_post_sprint_idle():
    assert is_post_sprint_idle({'status': 'post_sprint_idle'})


def test_is_post_sprint_idle_active_returns_false():
    assert not is_post_sprint_idle({'status': 'sprint_active'})


def test_is_post_sprint_idle_missing_status_returns_false():
    assert not is_post_sprint_idle({})


def test_is_post_sprint_idle_none_status_returns_false():
    assert not is_post_sprint_idle({'status': None})
