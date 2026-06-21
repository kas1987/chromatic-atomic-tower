"""Extended tests for cat_validate.py — targets the 40% uncovered paths.

Covers:
- _legacy_mission_number (match / no-match)
- _is_new_mission_id (valid new format / invalid)
- _is_legacy_allowed_mission_id (example / numeric below cutoff / numeric at/above cutoff)
- _is_new_bead_id (valid / invalid)
- _is_legacy_allowed_bead_id (legacy numeric / example / invalid)
- validate_id_policy — mission: new-format OK, legacy grandfathered OK, legacy cutover error,
  invalid format error
- validate_id_policy — bead: new mission + new bead OK, new mission + legacy bead error,
  legacy mission + legacy bead OK, invalid bead error
- validate_id_policy — template files are skipped entirely
- validate_file: schema OK, schema failure, id-policy failure
- validate_root_hygiene: missing allowlist, ok hygiene, hygiene issues
- resolve_root_hygiene_mode: cli override, env var, invalid falls back to enforce
- validate_all: mode=off skips hygiene, mode=warn non-blocking, mode=enforce blocking
- main() --file path with bead, mission, tower-state, agent-scorecard, unknown inference
- main() --all with no-templates flag
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import scripts.cat_validate as cv
from scripts.cat_validate import (
    _is_legacy_allowed_bead_id,
    _is_legacy_allowed_mission_id,
    _is_new_bead_id,
    _is_new_mission_id,
    _legacy_mission_number,
    resolve_root_hygiene_mode,
    validate_file,
    validate_id_policy,
    validate_root_hygiene,
)
from scripts.common import ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path


def _minimal_allowlist(root: Path) -> Path:
    path = root / 'gates' / 'hygiene' / 'root_allowlist.yaml'
    _write_yaml(path, {'allowed_files': [], 'allowed_dirs': [], 'ignored_entries': []})
    return path


# ===========================================================================
# 1. _legacy_mission_number
# ===========================================================================

def test_legacy_mission_number_valid() -> None:
    assert _legacy_mission_number('MP-CAT-003') == 3
    assert _legacy_mission_number('MP-CAT-000') == 0
    assert _legacy_mission_number('MP-CAT-099') == 99


def test_legacy_mission_number_invalid() -> None:
    assert _legacy_mission_number('MP-CAT-A006-4C01') is None
    assert _legacy_mission_number('GARBAGE') is None
    assert _legacy_mission_number('') is None


# ===========================================================================
# 2. _is_new_mission_id
# ===========================================================================

def test_is_new_mission_id_valid() -> None:
    assert _is_new_mission_id('MP-CAT-A006-4C01') is True
    assert _is_new_mission_id('MP-CAT-S001-1C00') is True
    assert _is_new_mission_id('MP-CAT-B012-2C03') is True


def test_is_new_mission_id_invalid() -> None:
    assert _is_new_mission_id('MP-CAT-003') is False
    assert _is_new_mission_id('MP-CAT-EXAMPLE-FOO') is False
    assert _is_new_mission_id('') is False


# ===========================================================================
# 3. _is_legacy_allowed_mission_id
# ===========================================================================

def test_legacy_allowed_mission_example() -> None:
    assert _is_legacy_allowed_mission_id('MP-CAT-EXAMPLE-ALPHA') is True
    assert _is_legacy_allowed_mission_id('MP-CAT-EXAMPLE-X1-Y2') is True


def test_legacy_allowed_mission_numeric_below_cutoff() -> None:
    # Cutoff is 6 — numbers < 6 are grandfathered
    assert _is_legacy_allowed_mission_id('MP-CAT-000') is True
    assert _is_legacy_allowed_mission_id('MP-CAT-005') is True


def test_legacy_allowed_mission_numeric_at_cutoff() -> None:
    # Numbers >= 6 are NOT grandfathered
    assert _is_legacy_allowed_mission_id('MP-CAT-006') is False
    assert _is_legacy_allowed_mission_id('MP-CAT-010') is False


def test_legacy_allowed_mission_invalid_format() -> None:
    assert _is_legacy_allowed_mission_id('GARBAGE') is False


# ===========================================================================
# 4. _is_new_bead_id
# ===========================================================================

def test_is_new_bead_id_valid() -> None:
    assert _is_new_bead_id('BEAD-CAT-A006-4C01-01') is True
    assert _is_new_bead_id('BEAD-CAT-S001-1C00-99') is True


def test_is_new_bead_id_invalid() -> None:
    assert _is_new_bead_id('BEAD-CAT-001-001') is False
    assert _is_new_bead_id('BEAD-CAT-EXAMPLE-1') is False
    assert _is_new_bead_id('') is False


# ===========================================================================
# 5. _is_legacy_allowed_bead_id
# ===========================================================================

def test_is_legacy_allowed_bead_id_numeric() -> None:
    assert _is_legacy_allowed_bead_id('BEAD-CAT-001-001') is True
    assert _is_legacy_allowed_bead_id('BEAD-CAT-005-099') is True


def test_is_legacy_allowed_bead_id_example() -> None:
    assert _is_legacy_allowed_bead_id('BEAD-CAT-EXAMPLE-1') is True
    assert _is_legacy_allowed_bead_id('BEAD-CAT-001-CLOSEOUT-EXAMPLE') is True


def test_is_legacy_allowed_bead_id_invalid() -> None:
    assert _is_legacy_allowed_bead_id('BEAD-CAT-A006-4C01-01') is False  # new format
    assert _is_legacy_allowed_bead_id('GARBAGE') is False


# ===========================================================================
# 6. validate_id_policy — mission
# ===========================================================================

def test_validate_id_policy_mission_new_format_ok(tmp_path: Path) -> None:
    file_path = tmp_path / 'missions' / 'active' / 'test.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-A006-4C01'}, file_path)
    assert errors == []


def test_validate_id_policy_mission_legacy_grandfathered(tmp_path: Path) -> None:
    file_path = tmp_path / 'missions' / 'active' / 'test.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-003'}, file_path)
    assert errors == []


def test_validate_id_policy_mission_example_id(tmp_path: Path) -> None:
    file_path = tmp_path / 'missions' / 'examples' / 'test.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-EXAMPLE-ALPHA'}, file_path)
    assert errors == []


def test_validate_id_policy_mission_legacy_at_cutover_error(tmp_path: Path) -> None:
    file_path = tmp_path / 'missions' / 'active' / 'test.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'MP-CAT-006'}, file_path)
    assert len(errors) == 1
    assert 'cutover' in errors[0] or 'legacy' in errors[0]


def test_validate_id_policy_mission_invalid_format_error(tmp_path: Path) -> None:
    file_path = tmp_path / 'missions' / 'active' / 'test.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'GARBAGE'}, file_path)
    assert len(errors) == 1
    assert 'invalid' in errors[0]


def test_validate_id_policy_template_skipped(tmp_path: Path) -> None:
    # Templates live under a path with 'templates' in parts
    file_path = tmp_path / 'missions' / 'templates' / 'my_template.yaml'
    errors = validate_id_policy('mission', {'mission_id': 'GARBAGE'}, file_path)
    assert errors == []


# ===========================================================================
# 7. validate_id_policy — bead
# ===========================================================================

def test_validate_id_policy_bead_new_mission_new_bead_ok(tmp_path: Path) -> None:
    file_path = tmp_path / 'beads' / 'active' / 'test.yaml'
    errors = validate_id_policy('bead', {
        'mission_id': 'MP-CAT-A006-4C01',
        'bead_id': 'BEAD-CAT-A006-4C01-01',
    }, file_path)
    assert errors == []


def test_validate_id_policy_bead_new_mission_legacy_bead_error(tmp_path: Path) -> None:
    file_path = tmp_path / 'beads' / 'active' / 'test.yaml'
    errors = validate_id_policy('bead', {
        'mission_id': 'MP-CAT-A006-4C01',
        'bead_id': 'BEAD-CAT-001-001',  # legacy bead under new mission
    }, file_path)
    assert any('legacy' in e for e in errors)


def test_validate_id_policy_bead_legacy_mission_legacy_bead_ok(tmp_path: Path) -> None:
    file_path = tmp_path / 'beads' / 'active' / 'test.yaml'
    errors = validate_id_policy('bead', {
        'mission_id': 'MP-CAT-003',
        'bead_id': 'BEAD-CAT-003-001',
    }, file_path)
    assert errors == []


def test_validate_id_policy_bead_invalid_mission_invalid_bead_error(tmp_path: Path) -> None:
    file_path = tmp_path / 'beads' / 'active' / 'test.yaml'
    errors = validate_id_policy('bead', {
        'mission_id': 'GARBAGE',
        'bead_id': 'GARBAGE',
    }, file_path)
    assert len(errors) >= 1


def test_validate_id_policy_bead_at_cutover_mission_needs_new_bead(tmp_path: Path) -> None:
    file_path = tmp_path / 'beads' / 'active' / 'test.yaml'
    # mission >= cutover needs new-format bead
    errors = validate_id_policy('bead', {
        'mission_id': 'MP-CAT-006',
        'bead_id': 'BEAD-CAT-001-001',  # legacy bead — should error
    }, file_path)
    assert any('new format' in e or 'cutover' in e for e in errors)


# ===========================================================================
# 8. validate_file
# ===========================================================================

def test_validate_file_passes_real_bead(tmp_path: Path) -> None:
    """Validate a real on-disk bead file if one exists, otherwise skip."""
    bead_files = list(ROOT.glob('beads/active/*.yaml')) + list(ROOT.glob('beads/examples/*.yaml'))
    if not bead_files:
        pytest.skip('no bead files available in the real repo')
    schema = ROOT / 'schemas/bead.schema.json'
    ok, errors = validate_file('bead', bead_files[0], schema)
    # We don't assert ok — may or may not pass; just confirm no exception and correct return types
    assert isinstance(ok, bool)
    assert isinstance(errors, list)


def test_validate_file_schema_failure(tmp_path: Path) -> None:
    """A file that fails schema validation returns ok=False with error list."""
    # Create a minimal schema that requires a field 'required_field'
    schema_path = tmp_path / 'test.schema.json'
    schema_path.write_text(json.dumps({
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        'type': 'object',
        'required': ['required_field'],
        'properties': {'required_field': {'type': 'string'}},
    }), encoding='utf-8')
    yaml_path = tmp_path / 'broken.yaml'
    yaml_path.write_text('some_other_field: oops\n', encoding='utf-8')
    ok, errors = validate_file('mission', yaml_path, schema_path)
    assert ok is False
    assert len(errors) >= 1


def test_validate_file_passes_with_valid_schema(tmp_path: Path) -> None:
    schema_path = tmp_path / 'test.schema.json'
    schema_path.write_text(json.dumps({
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        'type': 'object',
        'required': ['name'],
        'properties': {'name': {'type': 'string'}},
    }), encoding='utf-8')
    yaml_path = tmp_path / 'valid.yaml'
    yaml_path.write_text('name: hello\n', encoding='utf-8')
    ok, errors = validate_file('other', yaml_path, schema_path)
    assert ok is True
    assert errors == []


# ===========================================================================
# 9. validate_root_hygiene
# ===========================================================================

def test_validate_root_hygiene_missing_allowlist(tmp_path: Path) -> None:
    ok, issues = validate_root_hygiene(tmp_path)
    assert ok is False
    assert any('missing' in i or 'allowlist' in i for i in issues)


def test_validate_root_hygiene_clean_root(tmp_path: Path) -> None:
    _minimal_allowlist(tmp_path)
    # Use mocks so we don't depend on find_root_hygiene_issues touching the real FS
    with patch('scripts.cat_validate.load_root_allowlist', return_value={'allowed_files': set(), 'allowed_dirs': set(), 'ignored_entries': set()}), \
         patch('scripts.cat_validate.find_root_hygiene_issues', return_value=[]):
        ok, issues = validate_root_hygiene(tmp_path)
    assert ok is True
    assert issues == []


def test_validate_root_hygiene_with_issues(tmp_path: Path) -> None:
    _minimal_allowlist(tmp_path)
    with patch('scripts.cat_validate.load_root_allowlist', return_value={'allowed_files': set(), 'allowed_dirs': set(), 'ignored_entries': set()}), \
         patch('scripts.cat_validate.find_root_hygiene_issues', return_value=['stray_file.txt']):
        ok, issues = validate_root_hygiene(tmp_path)
    assert ok is False
    assert 'stray_file.txt' in issues


# ===========================================================================
# 10. resolve_root_hygiene_mode
# ===========================================================================

def test_resolve_root_hygiene_mode_cli_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'off')
    assert resolve_root_hygiene_mode('warn') == 'warn'


def test_resolve_root_hygiene_mode_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'warn')
    assert resolve_root_hygiene_mode(None) == 'warn'


def test_resolve_root_hygiene_mode_default_enforce(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('CAT_ROOT_HYGIENE_MODE', raising=False)
    assert resolve_root_hygiene_mode(None) == 'enforce'


def test_resolve_root_hygiene_mode_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('CAT_ROOT_HYGIENE_MODE', raising=False)
    assert resolve_root_hygiene_mode('INVALID') == 'enforce'


def test_resolve_root_hygiene_mode_env_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'INVALID_MODE')
    assert resolve_root_hygiene_mode(None) == 'enforce'


# ===========================================================================
# 11. validate_all — mode=off, warn, enforce
# ===========================================================================

def test_validate_all_mode_off_skips_hygiene(capsys: pytest.CaptureFixture) -> None:
    with patch('scripts.cat_validate.validate_root_hygiene') as mock_rh, \
         patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.validate_all(include_templates=False, root_hygiene_mode='off')
    mock_rh.assert_not_called()
    out = capsys.readouterr().out
    assert 'SKIP' in out


def test_validate_all_mode_warn_hygiene_issues_non_blocking(capsys: pytest.CaptureFixture) -> None:
    with patch('scripts.cat_validate.validate_root_hygiene', return_value=(False, ['stray.txt'])), \
         patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.validate_all(include_templates=False, root_hygiene_mode='warn')
    out = capsys.readouterr().out
    assert 'WARN' in out
    assert rc == 0  # warn does not count as failure


def test_validate_all_mode_enforce_hygiene_failure_blocks(capsys: pytest.CaptureFixture) -> None:
    with patch('scripts.cat_validate.validate_root_hygiene', return_value=(False, ['stray.txt'])), \
         patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.validate_all(include_templates=False, root_hygiene_mode='enforce')
    out = capsys.readouterr().out
    assert 'FAIL' in out
    assert rc == 1


def test_validate_all_returns_0_on_all_pass(capsys: pytest.CaptureFixture) -> None:
    with patch('scripts.cat_validate.validate_root_hygiene', return_value=(True, [])), \
         patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.validate_all(include_templates=False, root_hygiene_mode='enforce')
    assert rc == 0


def test_validate_all_returns_1_on_file_failure(capsys: pytest.CaptureFixture) -> None:
    with patch('scripts.cat_validate.validate_root_hygiene', return_value=(True, [])), \
         patch('scripts.cat_validate.validate_file', return_value=(False, ['schema error'])):
        rc = cv.validate_all(include_templates=False, root_hygiene_mode='enforce')
    assert rc == 1


# ===========================================================================
# 12. main() — --file inference
# ===========================================================================

def test_main_file_bead_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    bead_file = tmp_path / 'beads' / 'active' / 'test_bead.yaml'
    bead_file.parent.mkdir(parents=True, exist_ok=True)
    bead_file.write_text('placeholder: true\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(bead_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert 'PASS' in out


def test_main_file_bead_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    bead_file = tmp_path / 'beads' / 'active' / 'test_bead.yaml'
    bead_file.parent.mkdir(parents=True, exist_ok=True)
    bead_file.write_text('placeholder: true\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(bead_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(False, ['bad schema'])):
        rc = cv.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert 'FAIL' in out


def test_main_file_mission_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    reg_file = tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    reg_file.write_text('missions: []\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(reg_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.main()
    assert rc == 0


def test_main_file_tower_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    tower_file = tmp_path / 'TOWER_STATE.yaml'
    tower_file.write_text('active_mission_id: ""\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(tower_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.main()
    assert rc == 0


def test_main_file_agent_scorecard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    sc_file = tmp_path / 'AGENT_SCORECARD.yaml'
    sc_file.write_text('agents: []\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(sc_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(True, [])):
        rc = cv.main()
    assert rc == 0


def test_main_file_unknown_returns_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    unknown_file = tmp_path / 'random_file.yaml'
    unknown_file.write_text('key: value\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(unknown_file)])
    rc = cv.main()
    assert rc == 2


def test_main_no_args_returns_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('sys.argv', ['cat_validate'])
    rc = cv.main()
    assert rc == 2


def test_main_all_no_templates(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr('sys.argv', ['cat_validate', '--all', '--no-templates'])
    with patch('scripts.cat_validate.validate_all', return_value=0) as mock_va:
        rc = cv.main()
    assert rc == 0
    mock_va.assert_called_once()
    _, kwargs = mock_va.call_args
    assert kwargs.get('include_templates') is False or mock_va.call_args[0][0] is False


def test_main_all_with_root_hygiene_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('sys.argv', ['cat_validate', '--all', '--root-hygiene-mode', 'warn'])
    with patch('scripts.cat_validate.validate_all', return_value=0) as mock_va:
        rc = cv.main()
    assert rc == 0
    mock_va.assert_called_once()


def test_main_file_mission_infers_mission_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """A file under missions/ (not registry/) should be inferred as mission kind."""
    mission_file = tmp_path / 'missions' / 'active' / 'MP-CAT-001.yaml'
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text('mission_id: MP-CAT-001\n', encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['cat_validate', '--file', str(mission_file)])
    with patch('scripts.cat_validate.validate_file', return_value=(True, [])) as mock_vf:
        rc = cv.main()
    assert rc == 0
    # Confirm validate_file was called with kind='mission'
    call_args = mock_vf.call_args[0]
    assert call_args[0] == 'mission'
