from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from cat_closeout import (
    run_closeout,
    append_closeout_event,
    write_closeout_report,
    utc_now,
)


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


# ---------------------------------------------------------------------------
# Additional coverage: error handling, report format, JSONL log
# ---------------------------------------------------------------------------

def test_closeout_blocks_failed_validation_result():
    """A bundle with validation_result=failed must be blocked."""
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-FAILED.yaml',
        'test failed result',
        'pytest',
        True,
        False,
    )
    assert code == 1
    assert event['allowed'] is False
    assert any('blocking validation result' in err for err in event['errors'])


def test_closeout_event_contains_required_fields():
    """The event dict must include all required audit fields."""
    required_fields = [
        'timestamp', 'target_type', 'target_id', 'to_status',
        'bundle', 'allowed', 'dry_run', 'reason', 'message',
    ]
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'field check',
        'pytest',
        True,
        False,
    )
    for field in required_fields:
        assert field in event, f"Missing required field: {field}"


def test_closeout_event_target_type_and_id_match_input():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'target check',
        'pytest',
        True,
        False,
    )
    assert event['target_type'] == 'bead'
    assert event['target_id'] == 'BEAD-CAT-002-CLOSEOUT-EXAMPLE'
    assert event['to_status'] == 'completed'


def test_closeout_event_message_allowed():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'message check',
        'pytest',
        True,
        False,
    )
    assert 'closeout allowed' in event['message']


def test_closeout_event_message_blocked_on_mismatch():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-DOES-NOT-MATCH',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'message blocked check',
        'pytest',
        True,
        False,
    )
    assert 'blocked' in event['message']


def test_closeout_actor_recorded_in_event():
    code, event = run_closeout(
        'bead',
        'BEAD-CAT-002-CLOSEOUT-EXAMPLE',
        'completed',
        'evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml',
        'actor check',
        'SpecialActor',
        True,
        False,
    )
    assert event['actor'] == 'SpecialActor'


def test_closeout_report_file_created(tmp_path, monkeypatch):
    """write_closeout_report creates a .md file in the configured report dir."""
    # Patch ROOT in cat_closeout to use tmp_path so we control the report dir.
    import cat_closeout as cc_module
    original_root = cc_module.ROOT
    monkeypatch.setattr(cc_module, 'ROOT', tmp_path)

    # Reproduce enough gate rules structure so load_rules works.
    gate_dir = tmp_path / 'gates' / 'evidence'
    gate_dir.mkdir(parents=True)
    rules = {
        'audit': {
            'report_dir': 'evidence/reports',
            'closeout_log': 'evidence/logs/closeouts.jsonl',
        },
        'validation_results': {'blocking': ['failed', 'blocked']},
        'targets': {},
    }
    (gate_dir / 'EVIDENCE_GATE_RULES.yaml').write_text(
        yaml.safe_dump(rules), encoding='utf-8'
    )

    event = {
        'timestamp': utc_now(),
        'target_type': 'bead',
        'target_id': 'BEAD-RPT-001',
        'to_status': 'completed',
        'bundle': 'evidence/bundles/test.yaml',
        'allowed': True,
        'dry_run': True,
        'reason': 'unit test',
        'message': 'closeout allowed',
    }
    bundle_data = {
        'summary': 'Test summary',
        'learning_note': 'Test learning note',
        'validation_result': 'passed',
        'required_artifacts': [],
        'supporting_artifacts': [],
    }
    report_path = write_closeout_report(event, bundle_data, [])
    assert report_path.exists()
    contents = report_path.read_text(encoding='utf-8')
    assert 'CAT Closeout Report' in contents
    assert 'BEAD-RPT-001' in contents
    assert 'Test summary' in contents


def test_append_closeout_event_writes_jsonl(tmp_path, monkeypatch):
    """append_closeout_event appends a JSON line to the log file."""
    import cat_closeout as cc_module
    monkeypatch.setattr(cc_module, 'ROOT', tmp_path)

    gate_dir = tmp_path / 'gates' / 'evidence'
    gate_dir.mkdir(parents=True)
    rules = {
        'audit': {
            'report_dir': 'evidence/reports',
            'closeout_log': 'evidence/logs/closeouts.jsonl',
        },
        'validation_results': {'blocking': ['failed', 'blocked']},
        'targets': {},
    }
    (gate_dir / 'EVIDENCE_GATE_RULES.yaml').write_text(
        yaml.safe_dump(rules), encoding='utf-8'
    )

    event = {
        'timestamp': utc_now(),
        'target_type': 'bead',
        'target_id': 'BEAD-LOG-001',
        'to_status': 'completed',
        'bundle': 'evidence/bundles/test.yaml',
        'allowed': True,
        'dry_run': False,
        'reason': 'test logging',
        'message': 'closeout allowed',
    }
    append_closeout_event(event)

    log_file = tmp_path / 'evidence' / 'logs' / 'closeouts.jsonl'
    assert log_file.exists()
    lines = log_file.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed['target_id'] == 'BEAD-LOG-001'
    assert parsed['allowed'] is True


def test_append_closeout_event_appends_multiple_lines(tmp_path, monkeypatch):
    """Multiple calls to append_closeout_event build up JSONL correctly."""
    import cat_closeout as cc_module
    monkeypatch.setattr(cc_module, 'ROOT', tmp_path)

    gate_dir = tmp_path / 'gates' / 'evidence'
    gate_dir.mkdir(parents=True)
    rules = {
        'audit': {
            'report_dir': 'evidence/reports',
            'closeout_log': 'evidence/logs/closeouts.jsonl',
        },
        'validation_results': {'blocking': ['failed', 'blocked']},
        'targets': {},
    }
    (gate_dir / 'EVIDENCE_GATE_RULES.yaml').write_text(
        yaml.safe_dump(rules), encoding='utf-8'
    )

    for i in range(3):
        append_closeout_event({
            'timestamp': utc_now(),
            'target_type': 'bead',
            'target_id': f'BEAD-MULTI-{i:03d}',
            'to_status': 'completed',
            'bundle': 'evidence/bundles/test.yaml',
            'allowed': True,
            'dry_run': False,
            'reason': 'multi-append test',
            'message': 'closeout allowed',
        })

    log_file = tmp_path / 'evidence' / 'logs' / 'closeouts.jsonl'
    lines = log_file.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 3
    ids = [json.loads(l)['target_id'] for l in lines]
    assert ids == ['BEAD-MULTI-000', 'BEAD-MULTI-001', 'BEAD-MULTI-002']


def test_closeout_report_contains_errors_section(tmp_path, monkeypatch):
    """write_closeout_report includes errors when provided."""
    import cat_closeout as cc_module
    monkeypatch.setattr(cc_module, 'ROOT', tmp_path)

    gate_dir = tmp_path / 'gates' / 'evidence'
    gate_dir.mkdir(parents=True)
    rules = {
        'audit': {
            'report_dir': 'evidence/reports',
            'closeout_log': 'evidence/logs/closeouts.jsonl',
        },
        'validation_results': {'blocking': ['failed', 'blocked']},
        'targets': {},
    }
    (gate_dir / 'EVIDENCE_GATE_RULES.yaml').write_text(
        yaml.safe_dump(rules), encoding='utf-8'
    )

    event = {
        'timestamp': utc_now(),
        'target_type': 'bead',
        'target_id': 'BEAD-ERR-001',
        'to_status': 'completed',
        'bundle': 'evidence/bundles/test.yaml',
        'allowed': False,
        'dry_run': True,
        'reason': 'unit test',
        'message': 'closeout blocked by evidence gate',
    }
    bundle_data = {
        'summary': 'Test summary',
        'learning_note': 'Test learning note',
        'validation_result': 'failed',
        'required_artifacts': [],
        'supporting_artifacts': [],
    }
    errors = ['missing required artifact: path/to/file.md', 'closeout_ready must be true']
    report_path = write_closeout_report(event, bundle_data, errors)
    contents = report_path.read_text(encoding='utf-8')
    assert '## Errors' in contents
    assert 'missing required artifact' in contents
    assert 'closeout_ready must be true' in contents


def test_closeout_report_none_errors_shows_none(tmp_path, monkeypatch):
    """write_closeout_report shows '- none' when no errors."""
    import cat_closeout as cc_module
    monkeypatch.setattr(cc_module, 'ROOT', tmp_path)

    gate_dir = tmp_path / 'gates' / 'evidence'
    gate_dir.mkdir(parents=True)
    rules = {
        'audit': {
            'report_dir': 'evidence/reports',
            'closeout_log': 'evidence/logs/closeouts.jsonl',
        },
        'validation_results': {'blocking': ['failed', 'blocked']},
        'targets': {},
    }
    (gate_dir / 'EVIDENCE_GATE_RULES.yaml').write_text(
        yaml.safe_dump(rules), encoding='utf-8'
    )

    event = {
        'timestamp': utc_now(),
        'target_type': 'bead',
        'target_id': 'BEAD-NOERR-001',
        'to_status': 'completed',
        'bundle': 'evidence/bundles/test.yaml',
        'allowed': True,
        'dry_run': True,
        'reason': 'unit test',
        'message': 'closeout allowed',
    }
    bundle_data = {
        'summary': 'Test summary',
        'learning_note': 'Test learning note',
        'validation_result': 'passed',
        'required_artifacts': [],
        'supporting_artifacts': [],
    }
    report_path = write_closeout_report(event, bundle_data, [])
    contents = report_path.read_text(encoding='utf-8')
    assert '- none' in contents
