"""BEAD-CAT-A014-4C01-02: Comprehensive tests for cat_closeout.py.

Tests cover:
  - Dry-run closeout with valid evidence bundle
  - Missing evidence blocks closeout (nonzero exit)
  - Bundle ID mismatch blocks closeout
  - Mission ID validation
  - Failed bundle blocks closeout
  - Closeout report is written
  - evidence_manifest.schema.json is valid JSON Schema
  - evidence/manifest.yaml exists
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_closeout import run_closeout
from scripts.common import ROOT, load_yaml


# ---------------------------------------------------------------------------
# Happy path: dry-run with valid bundle
# ---------------------------------------------------------------------------

class TestCloseoutHappyPath:
    def test_dry_run_allowed_with_valid_bundle(self):
        code, event = run_closeout(
            'bead',
            'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
            'completed',
            'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
            'test dry run',
            'pytest',
            dry_run=True,
            move=False,
        )
        assert code == 0
        assert event['allowed'] is True
        assert event['dry_run'] is True

    def test_dry_run_produces_closeout_report(self):
        """Closeout writes a report even in dry-run mode."""
        code, event = run_closeout(
            'bead',
            'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
            'completed',
            'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
            'test report generation',
            'pytest',
            dry_run=True,
            move=False,
        )
        assert 'report' in event
        report_path = ROOT / event['report']
        assert report_path.exists(), f"Closeout report not written: {report_path}"


# ---------------------------------------------------------------------------
# Missing evidence blocks closeout
# ---------------------------------------------------------------------------

class TestCloseoutBlocksMissingEvidence:
    def test_missing_artifact_blocks_closeout(self):
        code, event = run_closeout(
            'bead',
            'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
            'completed',
            'evidence/bundles/examples/EB-CAT-002-MISSING.yaml',
            'test missing artifact',
            'pytest',
            dry_run=True,
            move=False,
        )
        assert code == 1
        assert event['allowed'] is False
        assert any('missing required artifact' in e for e in event['errors'])


# ---------------------------------------------------------------------------
# ID mismatch blocks closeout
# ---------------------------------------------------------------------------

class TestCloseoutBlocksIdMismatch:
    def test_bead_id_mismatch_blocked(self):
        code, event = run_closeout(
            'bead',
            'BEAD-CAT-DOES-NOT-MATCH',
            'completed',
            'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
            'mismatch test',
            'pytest',
            dry_run=True,
            move=False,
        )
        assert code == 1
        assert event['allowed'] is False
        assert any('does not match' in e for e in event['errors'])

    def test_wrong_type_blocked(self):
        """Requesting mission closeout with a bead bundle is rejected."""
        code, event = run_closeout(
            'mission',
            'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
            'closed',
            'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
            'wrong type test',
            'pytest',
            dry_run=True,
            move=False,
        )
        assert code == 1
        assert event['allowed'] is False


# ---------------------------------------------------------------------------
# Failed bundle validation
# ---------------------------------------------------------------------------

class TestCloseoutFailedBundle:
    def test_failed_bundle_blocks_closeout(self):
        code, event = run_closeout(
            'bead',
            'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
            'completed',
            'evidence/bundles/examples/EB-CAT-002-FAILED.yaml',
            'failed bundle test',
            'pytest',
            dry_run=True,
            move=False,
        )
        # EB-CAT-002-FAILED.yaml has validation_result: failed
        assert code == 1
        assert event['allowed'] is False


# ---------------------------------------------------------------------------
# evidence_manifest.schema.json is valid
# ---------------------------------------------------------------------------

class TestEvidenceManifestSchema:
    def test_schema_file_exists(self):
        path = ROOT / 'schemas/evidence_manifest.schema.json'
        assert path.exists(), "schemas/evidence_manifest.schema.json not found"

    def test_schema_is_valid_json(self):
        path = ROOT / 'schemas/evidence_manifest.schema.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        assert isinstance(data, dict)
        assert '$schema' in data
        assert 'properties' in data

    def test_schema_requires_evidence_array(self):
        path = ROOT / 'schemas/evidence_manifest.schema.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        required = data.get('required', [])
        assert 'evidence' in required, "evidence_manifest schema must require 'evidence' array"

    def test_schema_entry_requires_sha256(self):
        path = ROOT / 'schemas/evidence_manifest.schema.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        entry_schema = data['properties']['evidence']['items']
        required = entry_schema.get('required', [])
        assert 'sha256' in required, "evidence entry must require sha256"


# ---------------------------------------------------------------------------
# evidence/manifest.yaml exists
# ---------------------------------------------------------------------------

class TestEvidenceManifestFile:
    def test_manifest_yaml_exists(self):
        path = ROOT / 'evidence/manifest.yaml'
        assert path.exists(), "evidence/manifest.yaml not found"

    def test_manifest_is_valid_yaml(self):
        data = load_yaml(ROOT / 'evidence/manifest.yaml')
        assert isinstance(data, dict)

    def test_manifest_has_schema_version(self):
        data = load_yaml(ROOT / 'evidence/manifest.yaml')
        assert 'schema_version' in data

    def test_manifest_has_evidence_key(self):
        data = load_yaml(ROOT / 'evidence/manifest.yaml')
        assert 'evidence' in data
        assert isinstance(data['evidence'], list)
