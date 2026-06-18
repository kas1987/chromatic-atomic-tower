"""BEAD-CAT-A014-4C01-03: Tests for cat_evidence_index.py.

Tests cover:
  - --check passes on a valid manifest
  - --check fails if required fields are missing
  - --check fails if artifact_path does not exist
  - --check fails on duplicate evidence_id
  - --rebuild creates a manifest with valid entries
  - --update-hashes replaces placeholder sha256 values
  - sha256 format validation
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_evidence_index import (
    rebuild_manifest,
    sha256_of,
    update_sha256,
    validate_manifest,
)
from scripts.common import ROOT


# ---------------------------------------------------------------------------
# validate_manifest
# ---------------------------------------------------------------------------

class TestValidateManifest:
    def test_valid_manifest_no_errors(self):
        data = {
            'schema_version': '0.1.0',
            'evidence': [
                {
                    'evidence_id': 'EVD-TEST-001',
                    'mission_id': 'MP-CAT-A014-4C01',
                    'bead_id': 'BEAD-CAT-A014-4C01-01',
                    'artifact_path': 'evidence/reports/state-transition-test-output.txt',
                    'artifact_type': 'test_output',
                    'generated_at': '2026-06-18T00:00:00+00:00',
                    'sha256': 'a' * 64,
                }
            ],
        }
        errors = validate_manifest(data)
        assert errors == [], errors

    def test_missing_schema_version(self):
        data = {'evidence': []}
        errors = validate_manifest(data)
        assert any('schema_version' in e for e in errors)

    def test_missing_required_field_in_entry(self):
        data = {
            'schema_version': '0.1.0',
            'evidence': [{'evidence_id': 'EVD-TEST-001'}],
        }
        errors = validate_manifest(data)
        assert any('mission_id' in e for e in errors)

    def test_duplicate_evidence_id_fails(self):
        entry = {
            'evidence_id': 'EVD-DUP-001',
            'mission_id': 'MP-CAT-A014-4C01',
            'bead_id': 'BEAD-CAT-A014-4C01-01',
            'artifact_path': 'evidence/reports/state-transition-test-output.txt',
            'artifact_type': 'test_output',
            'generated_at': '2026-06-18T00:00:00+00:00',
            'sha256': 'b' * 64,
        }
        data = {'schema_version': '0.1.0', 'evidence': [entry, entry.copy()]}
        errors = validate_manifest(data)
        assert any('duplicate' in e.lower() for e in errors)

    def test_missing_artifact_path_fails(self):
        data = {
            'schema_version': '0.1.0',
            'evidence': [
                {
                    'evidence_id': 'EVD-TEST-002',
                    'mission_id': 'MP-CAT-A014-4C01',
                    'bead_id': 'BEAD-CAT-A014-4C01-01',
                    'artifact_path': 'evidence/DOES_NOT_EXIST.txt',
                    'artifact_type': 'other',
                    'generated_at': '2026-06-18T00:00:00+00:00',
                    'sha256': 'c' * 64,
                }
            ],
        }
        errors = validate_manifest(data)
        assert any('does not exist' in e for e in errors)

    def test_invalid_sha256_fails(self):
        data = {
            'schema_version': '0.1.0',
            'evidence': [
                {
                    'evidence_id': 'EVD-TEST-003',
                    'mission_id': 'MP-CAT-A014-4C01',
                    'bead_id': 'BEAD-CAT-A014-4C01-01',
                    'artifact_path': 'evidence/reports/state-transition-test-output.txt',
                    'artifact_type': 'test_output',
                    'generated_at': '2026-06-18T00:00:00+00:00',
                    'sha256': 'not-a-hex-hash',
                }
            ],
        }
        errors = validate_manifest(data)
        assert any('sha256' in e for e in errors)


# ---------------------------------------------------------------------------
# rebuild_manifest
# ---------------------------------------------------------------------------

class TestRebuildManifest:
    def test_rebuild_returns_dict_with_evidence_list(self, tmp_path):
        # Create a minimal evidence directory with one file
        ev_dir = tmp_path / 'evidence' / 'reports'
        ev_dir.mkdir(parents=True)
        (ev_dir / 'sample.txt').write_text('test output\n', encoding='utf-8')
        data = rebuild_manifest(evidence_root=tmp_path / 'evidence')
        assert isinstance(data, dict)
        assert 'schema_version' in data
        assert isinstance(data.get('evidence'), list)
        assert len(data['evidence']) >= 1

    def test_rebuild_entries_have_required_fields(self, tmp_path):
        ev_dir = tmp_path / 'evidence' / 'reports'
        ev_dir.mkdir(parents=True)
        (ev_dir / 'output.txt').write_text('data', encoding='utf-8')
        data = rebuild_manifest(evidence_root=tmp_path / 'evidence')
        for entry in data['evidence']:
            assert 'evidence_id' in entry
            assert 'artifact_path' in entry
            assert 'sha256' in entry
            assert 'artifact_type' in entry


# ---------------------------------------------------------------------------
# sha256_of
# ---------------------------------------------------------------------------

class TestSha256Of:
    def test_sha256_length_is_64(self, tmp_path):
        f = tmp_path / 'test.txt'
        f.write_text('hello', encoding='utf-8')
        result = sha256_of(f)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_sha256_missing_file_returns_error_string(self, tmp_path):
        result = sha256_of(tmp_path / 'missing.txt')
        assert 'error' in result


# ---------------------------------------------------------------------------
# update_sha256
# ---------------------------------------------------------------------------

class TestUpdateSha256:
    def test_placeholder_replaced_with_real_hash(self):
        ev_path = 'evidence/reports/state-transition-test-output.txt'
        full = ROOT / ev_path
        if not full.exists():
            pytest.skip("evidence file not present")
        data = {
            'schema_version': '0.1.0',
            'evidence': [{
                'evidence_id': 'EVD-TEST-HASH',
                'mission_id': 'MP-CAT-A014-4C01',
                'bead_id': 'BEAD-CAT-A014-4C01-01',
                'artifact_path': ev_path,
                'artifact_type': 'test_output',
                'generated_at': '2026-06-18T00:00:00+00:00',
                'sha256': 'placeholder_to_be_updated_by_cat_evidence_index',
            }],
        }
        result = update_sha256(data)
        sha = result['evidence'][0]['sha256']
        assert len(sha) == 64
        assert all(c in '0123456789abcdef' for c in sha)


# ---------------------------------------------------------------------------
# Existing manifest is valid
# ---------------------------------------------------------------------------

class TestExistingManifest:
    def test_existing_manifest_passes_check(self):
        from scripts.common import load_yaml
        manifest_path = ROOT / 'evidence/manifest.yaml'
        if not manifest_path.exists():
            pytest.skip("manifest not found")
        data = load_yaml(manifest_path) or {}
        errors = validate_manifest(data)
        assert errors == [], f"Manifest errors: {errors}"
