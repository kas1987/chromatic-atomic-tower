from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from cat_validate import validate_id_policy


def test_mission_legacy_below_cutover_allowed():
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-005'}, Path('missions/active/MP-CAT-005.yaml'))
    assert errors == []


def test_mission_legacy_at_cutover_rejected():
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-006'}, Path('missions/active/MP-CAT-006.yaml'))
    assert any('at or above cutover' in err for err in errors)


def test_mission_new_format_allowed():
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-S001-4C01'}, Path('missions/backlog/MP-CAT-S001-4C01.yaml'))
    assert errors == []


def test_bead_new_mission_requires_new_bead_format():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-S001-4C01', 'bead_id': 'BEAD-CAT-005-001'},
        Path('beads/active/BEAD-CAT-005-001.yaml'),
    )
    assert any('legacy under new-format mission' in err for err in errors)


def test_bead_legacy_pair_below_cutover_allowed():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-005', 'bead_id': 'BEAD-CAT-005-001'},
        Path('beads/active/BEAD-CAT-005-001.yaml'),
    )
    assert errors == []


def test_bead_legacy_pair_at_cutover_rejected():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-006', 'bead_id': 'BEAD-CAT-006-001'},
        Path('beads/active/BEAD-CAT-006-001.yaml'),
    )
    assert any('at or above legacy cutover' in err for err in errors)


def test_bead_mission_stem_with_bead_prefix_is_allowed():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-A006-4C01', 'bead_id': 'BEAD-CAT-A006-4C01-01'},
        Path('beads/active/BEAD-CAT-A006-4C01-01.yaml'),
    )
    assert errors == []


def test_template_files_skip_id_policy():
    errors = validate_id_policy(
        'mission',
        {'mission_id': 'NOT-A-REAL-ID'},
        Path('missions/templates/M1_BASIC.yaml'),
    )
    assert errors == []
