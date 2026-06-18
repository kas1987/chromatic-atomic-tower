"""Tests for cat_validate.py — schema validation, ID policy, and evidence bundles."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from common import ROOT, load_yaml, validate_with_schema
from cat_validate import (
    NEW_MISSION_ID_RE,
    LEGACY_MISSION_ID_RE,
    EXAMPLE_MISSION_ID_RE,
    NEW_BEAD_ID_RE,
    LEGACY_BEAD_ID_RE,
    LEGACY_BEAD_EXAMPLE_RE,
    _is_new_mission_id,
    _is_legacy_allowed_mission_id,
    _is_new_bead_id,
    _is_legacy_allowed_bead_id,
    _legacy_mission_number,
    validate_id_policy,
    validate_file,
    resolve_root_hygiene_mode,
)


# ---------------------------------------------------------------------------
# Original static example tests (preserved)
# ---------------------------------------------------------------------------

def test_active_mission_validates():
    """When sprint is idle, validate the latest archived mission contract instead."""
    archived = ROOT / 'missions/archived/MP-CAT-A007-4C01_LOGHOUSE_INTELLIGENCE.yaml'
    active_dir = ROOT / 'missions/active'
    if archived.is_file():
        mission_path = archived
    else:
        active_missions = sorted(active_dir.glob('MP-CAT-*.yaml'))
        assert active_missions, 'expected at least one mission contract in active/ or archived A007'
        mission_path = active_missions[0]
    mission = load_yaml(mission_path)
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_archived_mission_validates():
    mission = load_yaml(ROOT / 'missions/archived/MP-CAT-000_ESTABLISH_CORE.yaml')
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_example_bead_validates():
    bead = load_yaml(ROOT / 'beads/examples/BEAD-CAT-EXAMPLE-001.yaml')
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors == []


def test_go_resolver_script_exists():
    assert (ROOT / 'scripts/cat_resolve_go.py').is_file()


# ---------------------------------------------------------------------------
# Mission ID policy — valid IDs
# ---------------------------------------------------------------------------

def test_new_mission_id_formats_accepted():
    valid_ids = [
        'MP-CAT-S001-1C01',
        'MP-CAT-A006-4C01',
        'MP-CAT-B999-2C99',
        'MP-CAT-C000-3C00',
        'MP-CAT-S123-4C55',
    ]
    for mid in valid_ids:
        assert _is_new_mission_id(mid), f'Expected {mid!r} to match new mission ID pattern'


def test_legacy_mission_id_below_cutoff_allowed():
    # Numbers 000–005 are below the cutover of 6
    for num in range(6):
        mid = f'MP-CAT-{num:03d}'
        assert _is_legacy_allowed_mission_id(mid), f'Expected {mid!r} to be a grandfathered legacy ID'


def test_example_mission_ids_allowed():
    valid_examples = [
        'MP-CAT-EXAMPLE-001',
        'MP-CAT-EXAMPLE-ALPHA',
        'MP-CAT-EXAMPLE-A1B2',
    ]
    for mid in valid_examples:
        assert _is_legacy_allowed_mission_id(mid), f'Expected {mid!r} to be allowed as example ID'


def test_legacy_mission_number_extraction():
    assert _legacy_mission_number('MP-CAT-000') == 0
    assert _legacy_mission_number('MP-CAT-005') == 5
    assert _legacy_mission_number('MP-CAT-010') == 10
    assert _legacy_mission_number('MP-CAT-A006-4C01') is None
    assert _legacy_mission_number('NOT-A-MISSION') is None


# ---------------------------------------------------------------------------
# Mission ID policy — invalid IDs
# ---------------------------------------------------------------------------

def test_legacy_mission_id_at_or_above_cutoff_rejected(tmp_path):
    # Numbers 6 and above should be rejected
    for num in [6, 7, 10, 100]:
        mid = f'MP-CAT-{num:03d}'
        fake_path = tmp_path / 'missions/active/test.yaml'
        fake_path.parent.mkdir(parents=True, exist_ok=True)
        errors = validate_id_policy('mission', {'mission_id': mid}, fake_path)
        assert errors, f'Expected errors for legacy mission ID {mid!r} at/above cutover'
        assert 'cutover' in errors[0].lower() or 'legacy' in errors[0].lower()


def test_completely_invalid_mission_id_rejected(tmp_path):
    invalid_ids = [
        'INVALID-ID',
        'mp-cat-a006-4c01',   # lowercase
        'MP-CAT-Z001-4C01',   # Z is not in [SABC]
        'MP-CAT-A6-4C01',     # wrong numeric width
        '',
        'MP-CAT-',
    ]
    fake_path = tmp_path / 'missions/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    for mid in invalid_ids:
        errors = validate_id_policy('mission', {'mission_id': mid}, fake_path)
        assert errors, f'Expected errors for invalid mission ID {mid!r}'


def test_template_path_skips_id_validation(tmp_path):
    # Files in templates/ subdirectory should skip policy validation
    template_path = tmp_path / 'missions/templates/example.yaml'
    template_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('mission', {'mission_id': 'PLACEHOLDER-ID'}, template_path)
    assert errors == [], 'Templates should bypass ID policy validation'


# ---------------------------------------------------------------------------
# BEAD ID policy — valid IDs
# ---------------------------------------------------------------------------

def test_new_bead_id_formats_accepted():
    valid_ids = [
        'BEAD-CAT-A006-4C01-01',
        'BEAD-CAT-S001-1C01-99',
        'BEAD-CAT-B123-2C45-00',
    ]
    for bid in valid_ids:
        assert _is_new_bead_id(bid), f'Expected {bid!r} to match new bead ID pattern'


def test_legacy_bead_ids_allowed():
    legacy_ids = [
        'BEAD-CAT-000-001',
        'BEAD-CAT-005-099',
        'BEAD-CAT-EXAMPLE-1',
        'BEAD-CAT-EXAMPLE-001',
        'BEAD-CAT-000-CLOSEOUT-EXAMPLE',
    ]
    for bid in legacy_ids:
        assert _is_legacy_allowed_bead_id(bid), f'Expected {bid!r} to be a legacy-allowed bead ID'


def test_new_bead_under_new_mission_accepted(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('bead', {
        'bead_id': 'BEAD-CAT-A006-4C01-01',
        'mission_id': 'MP-CAT-A006-4C01',
    }, fake_path)
    assert errors == []


def test_legacy_bead_under_legacy_mission_accepted(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('bead', {
        'bead_id': 'BEAD-CAT-000-001',
        'mission_id': 'MP-CAT-000',
    }, fake_path)
    assert errors == []


# ---------------------------------------------------------------------------
# BEAD ID policy — invalid combinations
# ---------------------------------------------------------------------------

def test_legacy_bead_under_new_mission_rejected(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('bead', {
        'bead_id': 'BEAD-CAT-000-001',
        'mission_id': 'MP-CAT-A006-4C01',
    }, fake_path)
    assert errors, 'Legacy bead under new-format mission should produce an error'
    assert any('legacy' in e.lower() for e in errors)


def test_bead_under_legacy_at_cutover_requires_new_format(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    # Mission 006 is at/above cutover — bead must use new format
    errors = validate_id_policy('bead', {
        'bead_id': 'BEAD-CAT-006-001',
        'mission_id': 'MP-CAT-006',
    }, fake_path)
    assert errors, 'Old-style bead under mission at cutover should produce an error'


def test_invalid_bead_id_under_invalid_mission_reports_both(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('bead', {
        'bead_id': 'NOT-A-BEAD',
        'mission_id': 'NOT-A-MISSION',
    }, fake_path)
    assert len(errors) >= 2, 'Both mission_id and bead_id errors should be reported'


# ---------------------------------------------------------------------------
# Evidence bundle schema validation
# ---------------------------------------------------------------------------

def _minimal_evidence_bundle() -> dict:
    return {
        'evidence_id': 'EB-CAT-A006-4C01-01',
        'mission_id': 'MP-CAT-A006-4C01',
        'bead_id': 'BEAD-CAT-A006-4C01-01',
        'target_type': 'bead',
        'type': 'test_run',
        'summary': 'All tests pass',
        'validation_result': 'passed',
        'required_artifacts': [
            {'path': 'evidence/output.txt', 'kind': 'test_output', 'required': True}
        ],
        'supporting_artifacts': [],
        'created_by': 'agent-test',
        'created_at': '2026-06-18T00:00:00Z',
        'learning_note': 'Tests confirmed behavior',
        'closeout_ready': True,
    }


def test_valid_evidence_bundle_passes_schema():
    bundle = _minimal_evidence_bundle()
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors == [], f'Expected no errors, got: {errors}'


def test_evidence_bundle_missing_required_field():
    required_fields = [
        'evidence_id', 'mission_id', 'target_type', 'type', 'summary',
        'validation_result', 'required_artifacts', 'supporting_artifacts',
        'created_by', 'created_at', 'learning_note', 'closeout_ready',
    ]
    schema_path = ROOT / 'schemas/evidence_bundle.schema.json'
    for field in required_fields:
        bundle = _minimal_evidence_bundle()
        del bundle[field]
        errors = validate_with_schema(bundle, schema_path)
        assert errors, f'Expected error when {field!r} is missing from evidence bundle'


def test_evidence_bundle_wrong_target_type():
    bundle = _minimal_evidence_bundle()
    bundle['target_type'] = 'invalid_type'
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'target_type must be one of [bead, mission]'


def test_evidence_bundle_wrong_validation_result():
    bundle = _minimal_evidence_bundle()
    bundle['validation_result'] = 'unknown'
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'validation_result must be one of [passed, failed, skipped, blocked]'


def test_evidence_bundle_summary_too_short():
    bundle = _minimal_evidence_bundle()
    bundle['summary'] = 'Hi'
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'summary must be at least 5 characters'


def test_evidence_bundle_required_artifacts_empty():
    bundle = _minimal_evidence_bundle()
    bundle['required_artifacts'] = []
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'required_artifacts must have at least one item'


def test_evidence_bundle_artifact_missing_path():
    bundle = _minimal_evidence_bundle()
    bundle['required_artifacts'] = [{'kind': 'test_output', 'required': True}]
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'Artifact missing path should fail validation'


def test_evidence_bundle_artifact_bad_validation_result():
    bundle = _minimal_evidence_bundle()
    bundle['required_artifacts'] = [{
        'path': 'out.txt',
        'kind': 'test_output',
        'required': True,
        'validation_result': 'oops',
    }]
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'Artifact with invalid validation_result should fail'


def test_evidence_bundle_multiple_errors_all_reported():
    """A bundle with several broken fields should produce one error per broken field."""
    bundle = _minimal_evidence_bundle()
    bundle['target_type'] = 'bad'
    bundle['validation_result'] = 'nope'
    bundle['summary'] = 'Hi'
    bundle['required_artifacts'] = []
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert len(errors) >= 3, (
        f'Expected at least 3 cascaded errors for multi-field violations, got {len(errors)}: {errors}'
    )


def test_evidence_bundle_closeout_ready_must_be_bool():
    bundle = _minimal_evidence_bundle()
    bundle['closeout_ready'] = 'yes'
    errors = validate_with_schema(bundle, ROOT / 'schemas/evidence_bundle.schema.json')
    assert errors, 'closeout_ready must be boolean, not string'


# ---------------------------------------------------------------------------
# validate_file — filesystem integration
# ---------------------------------------------------------------------------

def test_validate_file_valid_mission(tmp_path):
    """validate_file should return (True, []) for a schema-valid + policy-valid mission."""
    mission_path = tmp_path / 'missions/active/MP-CAT-A006-4C01.yaml'
    mission_path.parent.mkdir(parents=True, exist_ok=True)
    mission_path.write_text(yaml.safe_dump({
        'mission_id': 'MP-CAT-A006-4C01',
        'title': 'Test mission title',
        'level': 'M3',
        'status': 'approved',
        'owner': 'operator',
        'priority': 1,
        'risk_level': 'low',
        'reversibility': 'high',
        'autonomy_level': 'L3',
        'confidence_minimum': 80,
        'objective': 'This is a valid objective statement.',
        'scope': {'in': ['scripts/'], 'out': ['README.md']},
        'allowed_paths': ['scripts/'],
        'forbidden_paths': [],
        'acceptance_criteria': ['All tests pass'],
        'required_validation': [],
        'rollback': {'required': False, 'plan': 'revert'},
        'human_gate': {'required': False, 'approver': 'operator'},
        'tool_budget': {'search': 10, 'read': 20, 'write': 5, 'execute': 5, 'max_runtime_minutes': 30},
        'beads': [],
        'evidence_requirements': [],
    }), encoding='utf-8')
    ok, errors = validate_file('mission', mission_path, ROOT / 'schemas/mission.schema.json')
    assert ok, f'Expected valid mission to pass, got errors: {errors}'
    assert errors == []


def test_validate_file_invalid_mission_id_policy(tmp_path):
    """validate_file should catch legacy-above-cutover mission IDs."""
    mission_path = tmp_path / 'missions/active/MP-CAT-010.yaml'
    mission_path.parent.mkdir(parents=True, exist_ok=True)
    mission_path.write_text(yaml.safe_dump({
        'mission_id': 'MP-CAT-010',   # 10 >= 6 cutover
        'title': 'Test',
        'level': 'M3',
        'status': 'approved',
        'owner': 'op',
        'priority': 1,
        'risk_level': 'low',
        'reversibility': 'high',
        'autonomy_level': 'L3',
        'confidence_minimum': 80,
        'objective': 'This is a valid objective statement.',
        'scope': {'in': ['scripts/'], 'out': []},
        'allowed_paths': ['scripts/'],
        'forbidden_paths': [],
        'acceptance_criteria': ['done'],
        'required_validation': [],
        'rollback': {'required': False, 'plan': 'revert'},
        'human_gate': {'required': False, 'approver': 'op'},
        'tool_budget': {'search': 5, 'read': 5, 'write': 5, 'execute': 5, 'max_runtime_minutes': 10},
        'beads': [],
        'evidence_requirements': [],
    }), encoding='utf-8')
    ok, errors = validate_file('mission', mission_path, ROOT / 'schemas/mission.schema.json')
    assert not ok
    assert any('cutover' in e.lower() or 'legacy' in e.lower() for e in errors)


def test_validate_file_missing_required_schema_fields(tmp_path):
    """validate_file should surface schema errors for missing required fields."""
    mission_path = tmp_path / 'missions/active/incomplete.yaml'
    mission_path.parent.mkdir(parents=True, exist_ok=True)
    mission_path.write_text(yaml.safe_dump({'mission_id': 'MP-CAT-A999-1C01', 'title': 'Incomplete'}),
                            encoding='utf-8')
    ok, errors = validate_file('mission', mission_path, ROOT / 'schemas/mission.schema.json')
    assert not ok
    assert errors


def test_validate_file_valid_evidence_bundle(tmp_path):
    bundle_path = tmp_path / 'evidence/bundles/examples/EB-TEST.yaml'
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(yaml.safe_dump(_minimal_evidence_bundle()), encoding='utf-8')
    ok, errors = validate_file('evidence bundle', bundle_path, ROOT / 'schemas/evidence_bundle.schema.json')
    assert ok, f'Expected valid evidence bundle to pass, got: {errors}'


def test_validate_file_invalid_evidence_bundle(tmp_path):
    bundle = _minimal_evidence_bundle()
    bundle['validation_result'] = 'NOPE'
    bundle_path = tmp_path / 'evidence/bundles/examples/EB-BAD.yaml'
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(yaml.safe_dump(bundle), encoding='utf-8')
    ok, errors = validate_file('evidence bundle', bundle_path, ROOT / 'schemas/evidence_bundle.schema.json')
    assert not ok
    assert errors


# ---------------------------------------------------------------------------
# Edge cases — empty / None / malformed inputs
# ---------------------------------------------------------------------------

def test_validate_id_policy_empty_mission_id(tmp_path):
    fake_path = tmp_path / 'missions/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('mission', {'mission_id': ''}, fake_path)
    assert errors, 'Empty mission_id should be rejected'


def test_validate_id_policy_missing_mission_id_key(tmp_path):
    fake_path = tmp_path / 'missions/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('mission', {}, fake_path)
    assert errors, 'Missing mission_id key should produce an error'


def test_validate_id_policy_none_mission_id(tmp_path):
    fake_path = tmp_path / 'missions/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('mission', {'mission_id': None}, fake_path)
    assert errors, 'None mission_id should be rejected'


def test_validate_id_policy_bead_empty_ids(tmp_path):
    fake_path = tmp_path / 'beads/active/test.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('bead', {'bead_id': '', 'mission_id': ''}, fake_path)
    assert errors, 'Empty bead_id and mission_id should produce errors'


def test_validate_id_policy_unknown_kind_returns_empty(tmp_path):
    fake_path = tmp_path / 'other/file.yaml'
    fake_path.parent.mkdir(parents=True, exist_ok=True)
    errors = validate_id_policy('unknown_kind', {'mission_id': 'anything'}, fake_path)
    assert errors == [], 'Unknown kind should produce no errors (not a mission or bead)'


# ---------------------------------------------------------------------------
# resolve_root_hygiene_mode
# ---------------------------------------------------------------------------

def test_resolve_root_hygiene_mode_defaults_to_enforce(monkeypatch):
    monkeypatch.delenv('CAT_ROOT_HYGIENE_MODE', raising=False)
    assert resolve_root_hygiene_mode(None) == 'enforce'


def test_resolve_root_hygiene_mode_cli_overrides_env(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'warn')
    assert resolve_root_hygiene_mode('off') == 'off'


def test_resolve_root_hygiene_mode_invalid_falls_back_to_enforce(monkeypatch):
    monkeypatch.delenv('CAT_ROOT_HYGIENE_MODE', raising=False)
    assert resolve_root_hygiene_mode('banana') == 'enforce'


def test_resolve_root_hygiene_mode_env_warn(monkeypatch):
    monkeypatch.setenv('CAT_ROOT_HYGIENE_MODE', 'warn')
    assert resolve_root_hygiene_mode(None) == 'warn'


def test_resolve_root_hygiene_mode_off(monkeypatch):
    monkeypatch.delenv('CAT_ROOT_HYGIENE_MODE', raising=False)
    assert resolve_root_hygiene_mode('off') == 'off'


# ---------------------------------------------------------------------------
# Mission schema validation — required field granularity
# ---------------------------------------------------------------------------

def _minimal_mission() -> dict:
    return {
        'mission_id': 'MP-CAT-A006-4C01',
        'title': 'Test mission',
        'level': 'M3',
        'status': 'approved',
        'owner': 'operator',
        'priority': 1,
        'risk_level': 'low',
        'reversibility': 'high',
        'autonomy_level': 'L3',
        'confidence_minimum': 80,
        'objective': 'This is a valid objective statement.',
        'scope': {'in': ['scripts/'], 'out': []},
        'allowed_paths': ['scripts/'],
        'forbidden_paths': [],
        'acceptance_criteria': ['All tests pass'],
        'required_validation': [],
        'rollback': {'required': False, 'plan': 'revert'},
        'human_gate': {'required': False, 'approver': 'operator'},
        'tool_budget': {'search': 10, 'read': 20, 'write': 5, 'execute': 5, 'max_runtime_minutes': 30},
        'beads': [],
        'evidence_requirements': [],
    }


def test_mission_schema_valid_passes():
    errors = validate_with_schema(_minimal_mission(), ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_mission_schema_invalid_level():
    mission = _minimal_mission()
    mission['level'] = 'M9'
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors


def test_mission_schema_invalid_status():
    mission = _minimal_mission()
    mission['status'] = 'winging_it'
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors


def test_mission_schema_priority_out_of_range():
    mission = _minimal_mission()
    mission['priority'] = 6   # max is 5
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors


def test_mission_schema_objective_too_short():
    mission = _minimal_mission()
    mission['objective'] = 'Short'
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors


def test_mission_schema_empty_allowed_paths():
    mission = _minimal_mission()
    mission['allowed_paths'] = []
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors, 'allowed_paths must have at least one item'


# ---------------------------------------------------------------------------
# BEAD schema validation
# ---------------------------------------------------------------------------

def _minimal_bead() -> dict:
    return {
        'bead_id': 'BEAD-CAT-A006-4C01-01',
        'mission_id': 'MP-CAT-A006-4C01',
        'title': 'Test BEAD',
        'status': 'active',
        'agent_role': 'implementer',
        'autonomy_level': 'L3',
        'objective': 'Implement the required changes.',
        'allowed_paths': ['scripts/'],
        'forbidden_paths': [],
        'tool_budget': {'search': 10, 'read': 20, 'write': 5, 'execute': 5, 'max_runtime_minutes': 30},
        'confidence': {
            'minimum': 80, 'current': 90,
            'objective_clarity': 90, 'scope_clarity': 85,
            'evidence_quality': 80, 'reversibility': 90,
            'tool_fit': 85, 'risk_awareness': 80, 'testability': 90,
        },
        'risk_level': 'low',
        'reversibility': 'high',
        'stop_conditions': ['Confidence drops below 70'],
        'definition_of_done': ['All tests pass'],
        'validation': [],
        'required_output': ['evidence/output.txt'],
        'handoff': {},
    }


def test_bead_schema_valid_passes():
    errors = validate_with_schema(_minimal_bead(), ROOT / 'schemas/bead.schema.json')
    assert errors == []


def test_bead_schema_invalid_status():
    bead = _minimal_bead()
    bead['status'] = 'super_active'
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors


def test_bead_schema_empty_stop_conditions():
    bead = _minimal_bead()
    bead['stop_conditions'] = []
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors, 'stop_conditions must have at least one item'


def test_bead_schema_empty_definition_of_done():
    bead = _minimal_bead()
    bead['definition_of_done'] = []
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors, 'definition_of_done must have at least one item'


def test_bead_schema_confidence_out_of_range():
    bead = _minimal_bead()
    bead['confidence']['current'] = 150
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors, 'confidence.current above 100 should fail'
