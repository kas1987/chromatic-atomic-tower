#!/usr/bin/env python3
"""Test archival engine CLI."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import cat_archive_evidence as cae


def test_classify_eligibility_exempted():
    """Scorecard paths are exempted."""
    result = cae.classify_eligibility('agents/scorecards/BEAD-CAT-A011-4C01-01_Builder.yaml')
    assert result == 'exempted'


def test_classify_eligibility_eligible():
    """CI report paths are eligible."""
    result = cae.classify_eligibility('evidence/ci/cat_ci_report_MP_CAT_A011_4C01.json')
    assert result == 'eligible'


def test_classify_eligibility_unknown():
    """Unknown paths are classified as unknown."""
    result = cae.classify_eligibility('evidence/unknown/some_file.json')
    assert result == 'unknown'


def test_create_archive_record_archived():
    """Create archived event record."""
    record = cae.create_archive_record(
        source_path='evidence/ci/report.json',
        destination_path='evidence/archive/2026/Q2/report.json',
        file_size_bytes=1000,
        event='archived',
        eligibility='eligible',
        age_days=95,
        batch_id='batch_001',
    )
    assert record['event'] == 'archived'
    assert record['eligibility'] == 'eligible'
    assert record['source_path'] == 'evidence/ci/report.json'
    assert 'timestamp' in record


def test_create_archive_record_skipped():
    """Create skipped event record with reason."""
    record = cae.create_archive_record(
        source_path='agents/scorecards/record.yaml',
        destination_path=None,
        file_size_bytes=256,
        event='skipped',
        eligibility='exempted',
        reason='Scorecard records retained indefinitely',
        age_days=100,
        batch_id='batch_001',
    )
    assert record['event'] == 'skipped'
    assert record['destination_path'] is None
    assert record['reason'] == 'Scorecard records retained indefinitely'


def test_create_archive_record_failed():
    """Create failed event record."""
    record = cae.create_archive_record(
        source_path='evidence/logs/file.jsonl',
        destination_path=None,
        file_size_bytes=5000,
        event='failed',
        eligibility='eligible',
        reason='File not found',
        age_days=50,
        batch_id='batch_001',
    )
    assert record['event'] == 'failed'
    assert 'File not found' in record['reason']


def test_get_quarter_q1():
    """January-March is Q1."""
    date = datetime(2026, 2, 15)
    assert cae.get_quarter(date) == 'Q1'


def test_get_quarter_q2():
    """April-June is Q2."""
    date = datetime(2026, 5, 15)
    assert cae.get_quarter(date) == 'Q2'


def test_get_quarter_q3():
    """July-September is Q3."""
    date = datetime(2026, 8, 15)
    assert cae.get_quarter(date) == 'Q3'


def test_get_quarter_q4():
    """October-December is Q4."""
    date = datetime(2026, 11, 15)
    assert cae.get_quarter(date) == 'Q4'


def test_archive_destination_format(tmp_path):
    """Archive destination follows YYYY/QN/ structure."""
    test_file = tmp_path / 'test.json'
    test_file.write_text('{}')

    dest = cae.archive_destination(test_file)
    assert 'archive' in str(dest)
    assert '/Q' in str(dest)  # Contains quarter marker
    assert 'test.json' in str(dest)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
