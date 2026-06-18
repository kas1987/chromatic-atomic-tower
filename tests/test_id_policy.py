from pathlib import Path
import sys

_scripts_path = str(Path(__file__).resolve().parents[1] / 'scripts')
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

from cat_validate import validate_id_policy, resolve_root_hygiene_mode


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


# ===========================================================================
# Mission ID — boundary and format edge cases
# ===========================================================================

def test_mission_legacy_zero_allowed():
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-000'}, Path('missions/active/MP-CAT-000.yaml'))
    assert errors == []


def test_mission_legacy_all_below_cutover_allowed():
    for num in range(0, 6):  # 000 through 005 inclusive
        mid = f'MP-CAT-{num:03d}'
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/{mid}.yaml'))
        assert errors == [], f'{mid} should be allowed (below cutover)'


def test_mission_legacy_above_cutover_all_rejected():
    for num in [6, 7, 10, 50, 999]:
        mid = f'MP-CAT-{num:03d}'
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/{mid}.yaml'))
        assert any('at or above cutover' in e for e in errors), f'{mid} should be rejected'


def test_mission_example_id_allowed():
    for mid in ['MP-CAT-EXAMPLE-FOO', 'MP-CAT-EXAMPLE-001', 'MP-CAT-EXAMPLE-A1-B2']:
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/{mid}.yaml'))
        assert errors == [], f'{mid} should be allowed as example id'


def test_mission_totally_invalid_id_rejected():
    for mid in ['', 'INVALID', 'MP-CAT', 'MP-CAT-S001']:
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/file.yaml'))
        assert errors, f'{mid!r} should be rejected as invalid'


def test_mission_new_format_all_tiers_allowed():
    for tier in ['S', 'A', 'B', 'C']:
        mid = f'MP-CAT-{tier}001-4C01'
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/{mid}.yaml'))
        assert errors == [], f'{mid} should be allowed (tier {tier})'


def test_mission_new_format_invalid_tier_rejected():
    for tier in ['D', 'E', 'Z', '1']:
        mid = f'MP-CAT-{tier}001-4C01'
        errors = validate_id_policy('mission', {'mission_id': mid}, Path(f'missions/active/{mid}.yaml'))
        assert errors, f'{mid} should be rejected (invalid tier {tier!r})'


# ===========================================================================
# Bead ID — edge cases
# ===========================================================================

def test_bead_example_legacy_id_allowed():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-005', 'bead_id': 'BEAD-CAT-EXAMPLE-1'},
        Path('beads/active/BEAD-CAT-EXAMPLE-1.yaml'),
    )
    assert errors == []


def test_bead_closeout_example_id_allowed():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-005', 'bead_id': 'BEAD-CAT-005-CLOSEOUT-EXAMPLE'},
        Path('beads/active/BEAD-CAT-005-CLOSEOUT-EXAMPLE.yaml'),
    )
    assert errors == []


def test_bead_totally_invalid_id_under_new_mission_rejected():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-S001-4C01', 'bead_id': 'NOT-A-BEAD-ID'},
        Path('beads/active/NOT-A-BEAD-ID.yaml'),
    )
    assert errors


def test_bead_empty_bead_id_under_new_mission_rejected():
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-A006-4C01'},  # no bead_id key
        Path('beads/active/something.yaml'),
    )
    assert errors


def test_bead_legacy_mission_above_cutover_rejects_legacy_bead():
    # Both mission and bead IDs should draw errors
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-007', 'bead_id': 'BEAD-CAT-007-001'},
        Path('beads/active/BEAD-CAT-007-001.yaml'),
    )
    assert len(errors) >= 1


def test_bead_legacy_mission_above_cutover_new_bead_still_errors_on_mission():
    # Even with a valid new bead_id, the mission_id itself is invalid
    errors = validate_id_policy(
        'bead',
        {'mission_id': 'MP-CAT-010', 'bead_id': 'BEAD-CAT-A010-4C01-01'},
        Path('beads/active/BEAD-CAT-A010-4C01-01.yaml'),
    )
    mission_errors = [e for e in errors if 'mission_id' in e and 'cutover' in e]
    assert mission_errors


def test_bead_all_new_tier_formats_with_new_mission():
    for tier in ['S', 'A', 'B', 'C']:
        mission_id = f'MP-CAT-{tier}001-2C03'
        bead_id = f'BEAD-CAT-{tier}001-2C03-01'
        errors = validate_id_policy(
            'bead',
            {'mission_id': mission_id, 'bead_id': bead_id},
            Path(f'beads/active/{bead_id}.yaml'),
        )
        assert errors == [], f'{bead_id} under {mission_id} should be allowed'


# ===========================================================================
# resolve_root_hygiene_mode
# ===========================================================================

def test_resolve_mode_none_defaults_to_enforce():
    assert resolve_root_hygiene_mode(None) == 'enforce'


def test_resolve_mode_explicit_enforce():
    assert resolve_root_hygiene_mode('enforce') == 'enforce'


def test_resolve_mode_warn():
    assert resolve_root_hygiene_mode('warn') == 'warn'


def test_resolve_mode_off():
    assert resolve_root_hygiene_mode('off') == 'off'


def test_resolve_mode_invalid_returns_enforce():
    assert resolve_root_hygiene_mode('invalid') == 'enforce'
    assert resolve_root_hygiene_mode('ENFORCE') == 'enforce'
    assert resolve_root_hygiene_mode('yes') == 'enforce'


def test_resolve_mode_env_var_used_when_cli_none(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'warn')
    assert resolve_root_hygiene_mode(None) == 'warn'


def test_resolve_mode_env_var_off(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'off')
    assert resolve_root_hygiene_mode(None) == 'off'


def test_resolve_mode_cli_takes_precedence_over_env(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'off')
    assert resolve_root_hygiene_mode('warn') == 'warn'


def test_resolve_mode_env_var_invalid_returns_enforce(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'bad_mode')
    assert resolve_root_hygiene_mode(None) == 'enforce'
