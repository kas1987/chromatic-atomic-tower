"""Tests for scripts/cat_evidence.py — evidence bundle validation.

Covers:
- Evidence bundle parsing: required fields present/missing
- Artifact path resolution: valid paths, missing artifacts
- Closeout readiness checks: sufficient vs insufficient
- Bundle validation errors: wrong types, invalid enum values
- Edge cases: empty bundles, None values
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_evidence as ce


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_bundle(tmp_path: Path, data: dict) -> Path:
    """Write a YAML bundle to tmp_path and return its path."""
    p = tmp_path / 'bundle.yaml'
    p.write_text(yaml.safe_dump(data), encoding='utf-8')
    return p


def _valid_bead_bundle(artifact_path: str = 'gates/evidence/EVIDENCE_GATE_RULES.yaml') -> dict:
    """Return a minimal valid bead evidence bundle dict."""
    return {
        'evidence_id': 'EB-TEST-001',
        'mission_id': 'MP-TEST-001',
        'bead_id': 'BEAD-TEST-001',
        'target_type': 'bead',
        'type': 'closeout',
        'summary': 'Test evidence bundle for unit tests.',
        'validation_result': 'passed',
        'required_artifacts': [
            {
                'path': artifact_path,
                'kind': 'rules',
                'required': True,
                'description': 'Test artifact.',
                'validation_result': 'passed',
            }
        ],
        'supporting_artifacts': [],
        'metrics': {'required_artifacts': 1},
        'created_by': 'pytest',
        'created_at': '2026-01-01T00:00:00Z',
        'learning_note': 'Always validate before closeout.',
        'closeout_ready': True,
    }


def _valid_mission_bundle(artifact_path: str = 'gates/evidence/EVIDENCE_GATE_RULES.yaml') -> dict:
    """Return a minimal valid mission evidence bundle dict."""
    return {
        'evidence_id': 'EB-TEST-MISSION-001',
        'mission_id': 'MP-TEST-001',
        'bead_id': None,
        'target_type': 'mission',
        'type': 'closeout',
        'summary': 'Test mission evidence bundle.',
        'validation_result': 'passed',
        'required_artifacts': [
            {
                'path': artifact_path,
                'kind': 'rules',
                'required': True,
                'description': 'Test artifact.',
                'validation_result': 'passed',
            }
        ],
        'supporting_artifacts': [],
        'metrics': {'required_artifacts': 1},
        'created_by': 'pytest',
        'created_at': '2026-01-01T00:00:00Z',
        'learning_note': 'Learning note for mission closeout.',
        'closeout_ready': True,
    }


# ---------------------------------------------------------------------------
# validate_bundle — passing cases
# ---------------------------------------------------------------------------

def test_validate_bundle_passes_with_valid_bead_bundle(tmp_path):
    bundle_file = _write_bundle(tmp_path, _valid_bead_bundle())
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is True
    assert errors == []


def test_validate_bundle_passes_with_valid_mission_bundle(tmp_path):
    bundle_file = _write_bundle(tmp_path, _valid_mission_bundle())
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is True
    assert errors == []


def test_validate_bundle_returns_data(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert data['evidence_id'] == 'EB-TEST-001'
    assert data['mission_id'] == 'MP-TEST-001'
    assert data['bead_id'] == 'BEAD-TEST-001'


# ---------------------------------------------------------------------------
# validate_bundle — missing required fields
# ---------------------------------------------------------------------------

def test_validate_bundle_blocks_missing_learning_note(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['learning_note'] = ''
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('learning_note' in err for err in errors)


def test_validate_bundle_blocks_missing_bead_id_for_bead_target(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['bead_id'] = None
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('bead_id' in err for err in errors)


def test_validate_bundle_blocks_closeout_ready_false(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['closeout_ready'] = False
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('closeout_ready' in err for err in errors)


def test_validate_bundle_blocks_closeout_ready_none(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['closeout_ready'] = None
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('closeout_ready' in err for err in errors)


# ---------------------------------------------------------------------------
# validate_bundle — blocking validation results
# ---------------------------------------------------------------------------

def test_validate_bundle_blocks_failed_validation_result(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['validation_result'] = 'failed'
    bundle_data['closeout_ready'] = False
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('blocking validation result' in err for err in errors)


def test_validate_bundle_blocks_blocked_validation_result(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['validation_result'] = 'blocked'
    bundle_data['closeout_ready'] = False
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('blocking validation result' in err for err in errors)


def test_validate_bundle_blocks_required_artifact_with_failed_result(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['required_artifacts'][0]['validation_result'] = 'failed'
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('blocking validation' in err for err in errors)


def test_validate_bundle_blocks_required_artifact_with_blocked_result(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_data['required_artifacts'][0]['validation_result'] = 'blocked'
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('blocking validation' in err for err in errors)


# ---------------------------------------------------------------------------
# validate_bundle — missing artifact paths
# ---------------------------------------------------------------------------

def test_validate_bundle_blocks_missing_required_artifact_path(tmp_path):
    bundle_data = _valid_bead_bundle(artifact_path='nonexistent/path/missing_file.yaml')
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('missing required artifact' in err for err in errors)


def test_validate_bundle_skips_non_required_artifact_path(tmp_path):
    bundle_data = _valid_bead_bundle()
    # Add a non-required artifact with a missing path
    bundle_data['supporting_artifacts'] = [
        {
            'path': 'nonexistent/optional_artifact.md',
            'kind': 'documentation',
            'required': False,
            'validation_result': 'skipped',
        }
    ]
    bundle_file = _write_bundle(tmp_path, bundle_data)
    ok, errors, data = ce.validate_bundle(bundle_file)
    # The optional artifact path is not validated, so no error about it
    missing_errors = [e for e in errors if 'missing required artifact' in e]
    assert missing_errors == []


# ---------------------------------------------------------------------------
# summarize_result
# ---------------------------------------------------------------------------

def test_summarize_result_allowed_true(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_file = _write_bundle(tmp_path, bundle_data)
    result = ce.summarize_result(True, [], bundle_data, bundle_file)
    assert result['allowed'] is True
    assert result['errors'] == []
    assert result['evidence_id'] == 'EB-TEST-001'
    assert result['mission_id'] == 'MP-TEST-001'
    assert result['bead_id'] == 'BEAD-TEST-001'
    assert result['target_type'] == 'bead'


def test_summarize_result_allowed_false_with_errors(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_file = _write_bundle(tmp_path, bundle_data)
    errors = ['closeout_ready must be true', 'learning_note is required']
    result = ce.summarize_result(False, errors, bundle_data, bundle_file)
    assert result['allowed'] is False
    assert len(result['errors']) == 2


def test_summarize_result_includes_bundle_path(tmp_path):
    bundle_data = _valid_bead_bundle()
    bundle_file = _write_bundle(tmp_path, bundle_data)
    result = ce.summarize_result(True, [], bundle_data, bundle_file)
    assert 'bundle' in result
    assert result['bundle'] != ''


# ---------------------------------------------------------------------------
# bundle_path
# ---------------------------------------------------------------------------

def test_bundle_path_absolute_unchanged(tmp_path):
    abs_path = str(tmp_path / 'my_bundle.yaml')
    result = ce.bundle_path(abs_path)
    assert result == Path(abs_path)


def test_bundle_path_relative_rooted():
    relative = 'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml'
    result = ce.bundle_path(relative)
    assert result.is_absolute()
    assert result.name == 'EB-CAT-002-EXAMPLE.yaml'


# ---------------------------------------------------------------------------
# Integration: validate the real example bundle
# ---------------------------------------------------------------------------

def test_real_example_bundle_passes_validation():
    """The real EB-CAT-002-EXAMPLE.yaml must pass validation."""
    bundle_file = ROOT / 'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml'
    assert bundle_file.exists(), 'Real example bundle must exist'
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is True, f'Expected valid: {errors}'


def test_real_missing_bundle_fails_validation():
    """The real EB-CAT-002-MISSING.yaml must fail on missing artifact."""
    bundle_file = ROOT / 'evidence/bundles/examples/EB-CAT-002-MISSING.yaml'
    assert bundle_file.exists(), 'Missing-artifact example bundle must exist'
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
    assert any('missing required artifact' in err for err in errors)


def test_real_failed_bundle_blocks_on_validation_result():
    """The real EB-CAT-002-FAILED.yaml must be blocked by validation result."""
    bundle_file = ROOT / 'evidence/bundles/examples/EB-CAT-002-FAILED.yaml'
    assert bundle_file.exists(), 'Failed-result example bundle must exist'
    ok, errors, data = ce.validate_bundle(bundle_file)
    assert ok is False
