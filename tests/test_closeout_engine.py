from __future__ import annotations

import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.cat_closeout import run_closeout


def test_closeout_dry_run_allowed_with_valid_bundle():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'test dry run',
        'pytest',
        True,
        False,
    )
    assert code == 0
    assert event['allowed'] is True
    assert event['dry_run'] is True
    assert event['transition_event']['dry_run'] is True


def test_closeout_blocks_id_mismatch():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-DOES-NOT-MATCH',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'test mismatch',
        'pytest',
        True,
        False,
    )
    assert code == 1
    assert event['allowed'] is False
    assert any('does not match' in error for error in event['errors'])


def test_closeout_blocks_missing_artifact():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-MISSING.yaml',
        'test missing artifact',
        'pytest',
        True,
        False,
    )
    assert code == 1
    assert event['allowed'] is False
    assert any('missing required artifact' in error for error in event['errors'])
