"""Extended coverage for cat_pr_guard.py — main() and run_samples() paths.

Existing test_cat_pr_guard.py covers check_pr_body and check_templates unit tests.
This file covers run_samples() and main() directly (subprocess calls don't contribute
to coverage in the parent process).
"""
from __future__ import annotations

import sys

import pytest

from scripts.cat_pr_guard import check_pr_body, check_templates, run_samples, main


class TestRunSamples:
    def test_run_samples_exits_zero_on_clean_repo(self, capsys):
        result = run_samples()
        assert result == 0

    def test_run_samples_prints_pass_for_sample_pass(self, capsys):
        run_samples()
        out = capsys.readouterr().out
        assert 'SAMPLE_PASS' in out

    def test_run_samples_prints_pass_for_no_mission_sample(self, capsys):
        run_samples()
        out = capsys.readouterr().out
        assert 'SAMPLE_FAIL_NO_MISSION' in out

    def test_run_samples_prints_pass_for_no_bead_sample(self, capsys):
        run_samples()
        out = capsys.readouterr().out
        assert 'SAMPLE_FAIL_NO_BEAD' in out

    def test_run_samples_prints_template_pass(self, capsys):
        run_samples()
        out = capsys.readouterr().out
        assert 'templates' in out.lower()


class TestMainCheckSamples:
    def test_main_check_samples_exits_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-samples'])
        assert main() == 0

    def test_main_check_pr_valid_body(self, monkeypatch, capsys):
        body = (
            'Mission ID: MP-CAT-A014-4C01\n'
            'BEAD ID: BEAD-CAT-A014-4C01-05\n'
            'evidence/reports/out.txt\n'
        )
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-pr', body])
        result = main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'PASS' in out

    def test_main_check_pr_invalid_body(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-pr', 'just a summary'])
        result = main()
        assert result == 1
        out = capsys.readouterr().out
        assert 'FAIL' in out

    def test_main_check_pr_missing_mission(self, monkeypatch, capsys):
        body = 'BEAD ID: BEAD-CAT-A014-4C01-05\nevidence/reports/out.txt'
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-pr', body])
        result = main()
        assert result == 1
        out = capsys.readouterr().out
        assert 'Mission ID' in out

    def test_main_check_pr_missing_bead(self, monkeypatch, capsys):
        body = 'Mission ID: MP-CAT-A014-4C01\nevidence/reports/out.txt'
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-pr', body])
        result = main()
        assert result == 1
        out = capsys.readouterr().out
        assert 'BEAD ID' in out

    def test_main_check_pr_missing_evidence(self, monkeypatch, capsys):
        body = 'Mission ID: MP-CAT-A014-4C01\nBEAD ID: BEAD-CAT-A014-4C01-05'
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-pr', body])
        result = main()
        assert result == 1

    def test_main_check_templates_passes_on_real_repo(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py', '--check-templates'])
        result = main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'PASS' in out

    def test_main_no_args_prints_help_and_exits_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_pr_guard.py'])
        result = main()
        assert result == 1
