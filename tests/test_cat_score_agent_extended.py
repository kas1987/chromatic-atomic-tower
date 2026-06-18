"""Extended coverage for cat_score_agent.py main() and _print_diff paths.

Existing test_cat_score_agent.py covers compute_mutation, format_scorecard_entry,
dry_run=True (record_event), and --dry-run --sample CLI.
This file covers main() --dry-run with explicit args, --record, _print_diff,
and no-args help path.
"""
from __future__ import annotations

import sys

import pytest

import cat_score_agent as csa
from scripts.cat_score_agent import (
    _find_agent,
    _print_diff,
    compute_mutation,
    main,
)


# ---------------------------------------------------------------------------
# _print_diff
# ---------------------------------------------------------------------------

def _base_data(score: int = 70) -> dict:
    return {
        'score_policy': {'starting_score': 70, 'promote_threshold': 85, 'demote_threshold': 55},
        'agents': [
            {
                'role': 'Builder',
                'score': score,
                'completed_beads': 0,
                'failed_beads': 0,
                'incidents': 0,
                'current_trust': 'provisional',
                'history': [],
            }
        ],
        'last_updated': '2026-01-01T00:00:00+00:00',
    }


class TestPrintDiff:
    def test_prints_score_change(self, capsys):
        old = _base_data(70)
        new = compute_mutation(old, 'Builder', 'B-001', 'M-001', 'bead_completed',
                                timestamp='2026-01-01T00:00:00Z')
        _print_diff(old, new, 'Builder')
        out = capsys.readouterr().out
        assert '70' in out
        assert '75' in out  # +5 for bead_completed

    def test_prints_trust_level(self, capsys):
        old = _base_data(85)
        new = compute_mutation(old, 'Builder', 'B-001', 'M-001', 'bead_completed',
                                timestamp='2026-01-01T00:00:00Z')
        _print_diff(old, new, 'Builder')
        out = capsys.readouterr().out
        assert 'trust' in out

    def test_new_agent_shows_new_label(self, capsys):
        old = {'agents': [], 'score_policy': {}}
        new = compute_mutation(old, 'Auditor', 'B-001', 'M-001', 'bead_completed',
                                timestamp='2026-01-01T00:00:00Z')
        _print_diff(old, new, 'Auditor')
        out = capsys.readouterr().out
        assert '(new)' in out

    def test_prints_last_event(self, capsys):
        old = _base_data(70)
        new = compute_mutation(old, 'Builder', 'B-007', 'M-001', 'bead_completed',
                                timestamp='2026-01-01T00:00:00Z')
        _print_diff(old, new, 'Builder')
        out = capsys.readouterr().out
        assert 'bead_completed' in out
        assert 'B-007' in out


# ---------------------------------------------------------------------------
# main() — --dry-run with explicit args
# ---------------------------------------------------------------------------

class TestMainDryRunWithArgs:
    def test_dry_run_with_full_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--dry-run',
            '--role', 'Builder',
            '--bead-id', 'BEAD-CAT-A014-4C01-06',
            '--event', 'bead_completed',
        ])
        result = main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'DRY-RUN' in out

    def test_dry_run_missing_args_returns_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--dry-run',
            '--role', 'Builder',
            # missing --bead-id and --event
        ])
        result = main()
        assert result == 1

    def test_dry_run_with_mission_id(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--dry-run',
            '--role', 'Auditor',
            '--bead-id', 'BEAD-CAT-A014-4C01-01',
            '--event', 'bead_failed',
            '--mission-id', 'MP-CAT-A014-4C01',
        ])
        result = main()
        assert result == 0

    def test_dry_run_incident_event(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--dry-run',
            '--role', 'Builder',
            '--bead-id', 'BEAD-CAT-A014-4C01-03',
            '--event', 'incident',
            '--incident-count', '2',
        ])
        result = main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'DRY-RUN' in out


# ---------------------------------------------------------------------------
# main() — --sample (already tested; here for _print_diff coverage path)
# ---------------------------------------------------------------------------

class TestMainSample:
    def test_sample_prints_dry_run_marker(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_score_agent.py', '--sample'])
        result = main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'DRY-RUN' in out
        assert 'No files written' in out


# ---------------------------------------------------------------------------
# main() — --record (writes to real files; use monkeypatch to redirect paths)
# ---------------------------------------------------------------------------

class TestMainRecord:
    def test_record_missing_args_returns_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--record',
            '--role', 'Builder',
            # missing --bead-id and --event
        ])
        result = main()
        assert result == 1

    def test_record_writes_and_prints(self, monkeypatch, tmp_path, capsys):
        scorecard = tmp_path / 'AGENT_SCORECARD.yaml'
        scorecards_dir = tmp_path / 'scorecards'
        scorecards_dir.mkdir()

        import yaml
        scorecard.write_text(yaml.dump({
            'schema_version': '0.1.0',
            'score_policy': {
                'starting_score': 70,
                'promote_threshold': 85,
                'demote_threshold': 55,
            },
            'agents': [],
        }), encoding='utf-8')

        monkeypatch.setattr(csa, 'SCORECARD_PATH', scorecard)
        monkeypatch.setattr(csa, 'SCORECARDS_DIR', scorecards_dir)
        monkeypatch.setattr(sys, 'argv', [
            'cat_score_agent.py', '--record',
            '--role', 'TestRole',
            '--bead-id', 'BEAD-TEST-001',
            '--event', 'bead_completed',
        ])
        # Must call csa.main() (not the `main` imported from scripts.cat_score_agent)
        # so that monkeypatch.setattr(csa, 'SCORECARD_PATH', ...) is honoured —
        # otherwise main() looks up globals in the scripts.cat_score_agent namespace
        # and writes to the real scorecard file, corrupting subsequent tests.
        result = csa.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'Recorded' in out
        assert scorecard.exists()


# ---------------------------------------------------------------------------
# main() — no args → help + return 1
# ---------------------------------------------------------------------------

class TestMainNoArgs:
    def test_no_args_returns_one(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['cat_score_agent.py'])
        assert main() == 1
