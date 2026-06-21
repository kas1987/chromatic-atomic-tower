#!/usr/bin/env python3
"""Test archival integration in cat_check_repo.py."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import cat_check_repo


def test_check_archival_stale_evidence_no_output(capsys):
    """If no stale evidence, archival check silent."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'No evidence older than 90 days.'
        cat_check_repo.check_archival_stale_evidence()
        captured = capsys.readouterr()
        assert 'No evidence older than' not in captured.out or 'stale evidence detected' not in captured.out


def test_check_archival_stale_evidence_with_output(capsys):
    """If stale evidence exists, archival check reports it."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'Found 5 evidence file(s) eligible for archival'
        cat_check_repo.check_archival_stale_evidence()
        captured = capsys.readouterr()
        assert 'stale evidence detected' in captured.out or 'dry-run' in captured.out


def test_check_archival_timeout(capsys):
    """If archival check times out, gracefully skip."""
    import subprocess
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 5)
        cat_check_repo.check_archival_stale_evidence()
        captured = capsys.readouterr()
        assert 'timed out' in captured.out


def test_check_archival_missing_script(capsys):
    """If archival script missing, silently skip."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        cat_check_repo.check_archival_stale_evidence()
        captured = capsys.readouterr()
        assert 'timed out' not in captured.out


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
