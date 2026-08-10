from __future__ import annotations

from pathlib import Path

import pytest

from scripts.cat_align_common import id_matches_taxonomy
from scripts.cat_validate import NEW_WORK_LEGACY_NUMERIC_CUTOFF, taxonomy_patterns, validate_id_policy


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
