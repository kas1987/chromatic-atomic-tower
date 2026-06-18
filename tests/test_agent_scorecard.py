"""Tests for scripts/cat_agent_scorecard.py — trust scoring engine."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import cat_agent_scorecard as cas


@pytest.fixture()
def fresh_scorecard(tmp_path, monkeypatch):
    """Return a temporary scorecard path and patch the module to use it."""
    data = {
        'version': '1.0.0',
        'last_updated': '2026-06-18',
        'score_policy': {
            'starting_score': 70,
            'promote_threshold': 85,
            'demote_threshold': 55,
            'severe_incident_cap': 40,
        },
        'agents': [
            {
                'role': 'Builder',
                'score': 70.0,
                'completed_beads': 0,
                'failed_beads': 0,
                'incidents': 0,
                'current_trust': 'provisional',
                'history': [],
            },
            {
                'role': 'Reviewer',
                'score': 80.0,
                'completed_beads': 3,
                'failed_beads': 0,
                'incidents': 0,
                'current_trust': 'provisional',
                'history': [],
            },
        ],
    }
    sc_path = tmp_path / 'AGENT_SCORECARD.yaml'
    sc_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    monkeypatch.setattr(cas, 'SCORECARD_PATH', sc_path)
    monkeypatch.setattr(cas, 'ROOT', tmp_path)
    (tmp_path / 'agents' / 'scorecards').mkdir(parents=True, exist_ok=True)
    return sc_path


def _make_args(**kwargs):
    """Build a minimal argparse.Namespace for testing."""
    import argparse
    defaults = {'dry_run': True, 'role': 'Builder', 'bead': 'BEAD-CAT-TEST-01', 'note': ''}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestScoreBead:
    def test_completed_dry_run_no_write(self, fresh_scorecard):
        args = _make_args(command='score-bead', result='completed', dry_run=True)
        rc = cas.cmd_score_bead(args)
        assert rc == 0
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 70.0
        assert agent['completed_beads'] == 0

    def test_completed_execute_adds_5(self, fresh_scorecard):
        args = _make_args(command='score-bead', result='completed', dry_run=False)
        rc = cas.cmd_score_bead(args)
        assert rc == 0
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 75.0
        assert agent['completed_beads'] == 1
        assert len(agent['history']) == 1
        assert agent['history'][0]['event'] == 'bead_completed'
        assert agent['history'][0]['delta'] == 5

    def test_failed_execute_subtracts_10(self, fresh_scorecard):
        args = _make_args(command='score-bead', result='failed', dry_run=False)
        rc = cas.cmd_score_bead(args)
        assert rc == 0
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 60.0
        assert agent['failed_beads'] == 1

    def test_floor_enforced_after_many_failures(self, fresh_scorecard):
        for _ in range(10):
            args = _make_args(command='score-bead', result='failed', dry_run=False)
            cas.cmd_score_bead(args)
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] >= 40.0

    def test_unknown_role_returns_1(self, fresh_scorecard):
        args = _make_args(command='score-bead', result='completed', role='NoSuchRole', dry_run=True)
        rc = cas.cmd_score_bead(args)
        assert rc == 1

    def test_increment_file_written(self, fresh_scorecard, tmp_path):
        args = _make_args(command='score-bead', result='completed', dry_run=False)
        cas.cmd_score_bead(args)
        increments = list((tmp_path / 'agents' / 'scorecards').glob('*.yaml'))
        assert len(increments) == 1
        entry = yaml.safe_load(increments[0].read_text())
        assert entry['event'] == 'bead_completed'

    def test_rerun_same_bead_is_idempotent(self, fresh_scorecard):
        """A second score-bead for the same role/bead/event must not double-count."""
        args = _make_args(command='score-bead', result='completed', dry_run=False)
        assert cas.cmd_score_bead(args) == 0
        assert cas.cmd_score_bead(args) == 0  # retry
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 75.0           # +5 once, not +10
        assert agent['completed_beads'] == 1
        assert len(agent['history']) == 1

    def test_idempotent_via_history_when_increment_file_cleaned(self, fresh_scorecard, tmp_path):
        """Even if the increment file is removed, history alone blocks a re-score."""
        args = _make_args(command='score-bead', result='completed', dry_run=False)
        assert cas.cmd_score_bead(args) == 0
        # Simulate increment-file cleanup; history retains the entry.
        for inc in (tmp_path / 'agents' / 'scorecards').glob('*.yaml'):
            inc.unlink()
        assert cas.cmd_score_bead(args) == 0  # must still skip on history
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 75.0
        assert agent['completed_beads'] == 1


class TestPenalize:
    def test_penalize_dry_run_no_write(self, fresh_scorecard):
        args = _make_args(command='penalize', dry_run=True)
        rc = cas.cmd_penalize(args)
        assert rc == 0
        data = yaml.safe_load(fresh_scorecard.read_text())
        assert cas._find_agent(data['agents'], 'Builder')['score'] == 70.0

    def test_penalize_execute_subtracts_15(self, fresh_scorecard):
        args = _make_args(command='penalize', dry_run=False)
        rc = cas.cmd_penalize(args)
        assert rc == 0
        data = yaml.safe_load(fresh_scorecard.read_text())
        agent = cas._find_agent(data['agents'], 'Builder')
        assert agent['score'] == 55.0
        assert agent['incidents'] == 1
        assert agent['history'][0]['event'] == 'incident'

    def test_penalize_floor_at_40(self, fresh_scorecard):
        for _ in range(5):
            args = _make_args(command='penalize', dry_run=False)
            cas.cmd_penalize(args)
        data = yaml.safe_load(fresh_scorecard.read_text())
        assert cas._find_agent(data['agents'], 'Builder')['score'] >= 40.0


class TestPromote:
    def test_promote_below_threshold_fails(self, fresh_scorecard):
        args = _make_args(command='promote', dry_run=True)
        rc = cas.cmd_promote(args)
        assert rc == 1

    def test_promote_at_threshold_dry_run(self, fresh_scorecard, monkeypatch):
        data = yaml.safe_load(fresh_scorecard.read_text())
        cas._find_agent(data['agents'], 'Builder')['score'] = 90.0
        fresh_scorecard.write_text(yaml.safe_dump(data))
        args = _make_args(command='promote', dry_run=True)
        rc = cas.cmd_promote(args)
        assert rc == 0
        reloaded = yaml.safe_load(fresh_scorecard.read_text())
        assert cas._find_agent(reloaded['agents'], 'Builder')['current_trust'] == 'provisional'

    def test_promote_execute_sets_trusted(self, fresh_scorecard):
        data = yaml.safe_load(fresh_scorecard.read_text())
        cas._find_agent(data['agents'], 'Builder')['score'] = 90.0
        fresh_scorecard.write_text(yaml.safe_dump(data))
        args = _make_args(command='promote', dry_run=False)
        rc = cas.cmd_promote(args)
        assert rc == 0
        reloaded = yaml.safe_load(fresh_scorecard.read_text())
        assert cas._find_agent(reloaded['agents'], 'Builder')['current_trust'] == 'trusted'


class TestDemote:
    def test_demote_above_threshold_fails(self, fresh_scorecard):
        args = _make_args(command='demote', dry_run=True)
        rc = cas.cmd_demote(args)
        assert rc == 1

    def test_demote_at_threshold_execute(self, fresh_scorecard):
        data = yaml.safe_load(fresh_scorecard.read_text())
        cas._find_agent(data['agents'], 'Builder')['score'] = 50.0
        fresh_scorecard.write_text(yaml.safe_dump(data))
        args = _make_args(command='demote', dry_run=False)
        rc = cas.cmd_demote(args)
        assert rc == 0
        reloaded = yaml.safe_load(fresh_scorecard.read_text())
        assert cas._find_agent(reloaded['agents'], 'Builder')['current_trust'] == 'restricted'


class TestReport:
    def test_report_all_returns_0(self, fresh_scorecard, capsys):
        args = _make_args(command='report', role='', json=False)
        rc = cas.cmd_report(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'Builder' in out
        assert 'Reviewer' in out

    def test_report_single_role(self, fresh_scorecard, capsys):
        args = _make_args(command='report', role='Builder', json=False)
        rc = cas.cmd_report(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'Builder' in out
        assert 'Reviewer' not in out

    def test_report_json_output(self, fresh_scorecard, capsys):
        args = _make_args(command='report', role='', json=True)
        rc = cas.cmd_report(args)
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert 'agents' in parsed
        assert len(parsed['agents']) == 2

    def test_report_unknown_role_returns_1(self, fresh_scorecard):
        args = _make_args(command='report', role='Nobody', json=False)
        rc = cas.cmd_report(args)
        assert rc == 1
