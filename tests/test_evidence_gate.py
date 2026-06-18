from __future__ import annotations

import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from pathlib import Path

from scripts.cat_evidence import validate_bundle
from scripts.common import ROOT


def test_valid_bundle_passes():
    ok, errors, data = validate_bundle(ROOT / 'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml')
    assert ok, errors
    assert data['evidence_id'] == 'EB-CAT-002-EXAMPLE'


def test_missing_required_artifact_fails():
    ok, errors, _ = validate_bundle(ROOT / 'evidence/bundles/examples/EB-CAT-002-MISSING.yaml')
    assert not ok
    assert any('missing required artifact' in error for error in errors)


def test_failed_validation_blocks_bundle():
    ok, errors, _ = validate_bundle(ROOT / 'evidence/bundles/examples/EB-CAT-002-FAILED.yaml')
    assert not ok
    assert any('blocking validation result' in error or 'blocking validation' in error for error in errors)
