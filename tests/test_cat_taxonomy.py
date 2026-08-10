from __future__ import annotations

from pathlib import Path
import shutil

import yaml

import pytest

from scripts.cat_align_common import id_matches_taxonomy
from scripts.cat_validate import NEW_WORK_LEGACY_NUMERIC_CUTOFF, taxonomy_patterns, validate_id_policy
from scripts.cat_taxonomy_audit import audit_root


def test_patterns_are_derived_from_contract():
    patterns = taxonomy_patterns()
    assert patterns['contract']['version'] == '2.0.0'
    assert patterns['legacy_cutoff'] == 6
    assert patterns['mission'].fullmatch('MP-CAT-A023-4C01')
    assert patterns['bead'].fullmatch('BEAD-CAT-A023-4C01-02')


@pytest.mark.parametrize('mission_id', ['MP-CAT-000', 'MP-CAT-005', 'MP-CAT-EXAMPLE-M2'])
def test_preserved_mission_ids_remain_accepted(mission_id):
    assert id_matches_taxonomy('mission', mission_id)
    assert validate_id_policy('mission', {'mission_id': mission_id}, Path('missions/examples/sample.yaml')) == []


@pytest.mark.parametrize('bead_id', ['BEAD-CAT-005-001', 'BEAD-CAT-EXAMPLE-001', 'BEAD-CAT-002-CLOSEOUT-EXAMPLE'])
def test_preserved_bead_ids_remain_accepted(bead_id):
    assert id_matches_taxonomy('bead', bead_id)


def test_new_format_requires_mission_stem_for_beads():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-A023-4C01', 'bead_id': 'BEAD-CAT-A023-4C01-1'},
        Path('beads/active/sample.yaml'),
    )
    assert errors


def test_contract_cutover_is_not_reimplemented_in_test():
    assert NEW_WORK_LEGACY_NUMERIC_CUTOFF == taxonomy_patterns()['legacy_cutoff']


def test_invalid_ids_are_rejected_by_contract_adapter():
    assert not id_matches_taxonomy('mission', 'MP-CAT-Z023-4C01')
    assert not id_matches_taxonomy('bead', 'BEAD-CAT-A023-4C01-1')


def _write_fixture(root: Path, *, bad_stem: bool = False) -> None:
    (root / 'gates').mkdir(parents=True)
    shutil.copy(Path('gates/CAT_ID_TAXONOMY.yaml'), root / 'gates/CAT_ID_TAXONOMY.yaml')
    (root / 'missions/active').mkdir(parents=True)
    (root / 'beads/active').mkdir(parents=True)
    (root / 'evidence/reports').mkdir(parents=True)
    mission = {
        'mission_id': 'MP-CAT-A023-4C01', 'level': 'M4', 'priority': 1,
        'mission_class': 'A', 'dependencies': [],
    }
    bead = {
        'bead_id': 'BEAD-CAT-B023-4C01-01' if bad_stem else 'BEAD-CAT-A023-4C01-01',
        'mission_id': 'MP-CAT-A023-4C01', 'priority': 1, 'dependencies': [],
        'status': 'active', 'validation': [{'evidence_path': 'evidence/reports/fixture.md'}],
    }
    (root / 'missions/active/mission.yaml').write_text(yaml.safe_dump(mission), encoding='utf-8')
    (root / 'beads/active/bead.yaml').write_text(yaml.safe_dump(bead), encoding='utf-8')
    (root / 'evidence/reports/fixture.md').write_text('fixture evidence\n', encoding='utf-8')


def test_taxonomy_audit_clean_fixture(tmp_path):
    _write_fixture(tmp_path)
    result = audit_root(tmp_path)
    assert result['summary']['status'] == 'PASS'
    assert result['summary']['errors'] == 0


def test_taxonomy_audit_reports_bead_stem_asymmetry(tmp_path):
    _write_fixture(tmp_path, bad_stem=True)
    result = audit_root(tmp_path)
    assert result['summary']['status'] == 'FAIL'
    finding = next(item for item in result['findings'] if item['code'] == 'BEAD_STEM_MISMATCH')
    assert finding['source'] == 'beads/active/bead.yaml'
    assert finding['consumer'] == 'mission_id'


def test_a024_repaired_complexity_class_has_no_drift():
    result = audit_root(Path(__file__).resolve().parents[1])
    assert not [item for item in result['findings'] if item['code'] == 'COMPLEXITY_MISMATCH']


def test_a024_authorized_ledgers_have_numeric_priority():
    result = audit_root(Path(__file__).resolve().parents[1])
    invalid_authorized = [
        item for item in result['findings']
        if item['code'] == 'INVALID_PRIORITY'
        and item['source'].startswith(('beads/completed/', 'beads/failed/'))
    ]
    assert invalid_authorized == []


def test_a024_example_priority_is_explicit_compatibility():
    result = audit_root(Path(__file__).resolve().parents[1])
    example_findings = [
        item for item in result['disposition_register']
        if item['code'] == 'INVALID_PRIORITY'
        and item['source'].startswith('beads/examples/')
    ]
    assert example_findings
    assert {item['disposition'] for item in example_findings} == {'compatibility_exception'}
