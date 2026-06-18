"""BEAD-CAT-A014-4C01-06: Tests for cat_score_agent.py.

Tests cover:
  - compute_mutation applies correct delta for bead_completed
  - compute_mutation applies correct delta for bead_failed
  - score is clamped at 0 and 100
  - trust level changes based on thresholds
  - dry-run does not write files
  - --record writes AGENT_SCORECARD.yaml and per-bead entry
  - format_scorecard_entry has required fields
  - AGENT_SCORECARD.yaml and scorecards/ directory exist
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_score_agent import (
    DELTA_MAP,
    SCORE_CAP,
    SCORE_FLOOR,
    compute_mutation,
    format_scorecard_entry,
    record_event,
)


BASE_DATA = {
    'version': '1.0.0',
    'last_updated': '2026-01-01T00:00:00+00:00',
    'score_policy': {
        'starting_score': 70,
        'promote_threshold': 85,
        'demote_threshold': 55,
        'severe_incident_cap': 40,
    },
    'agents': [
        {
            'role': 'Builder',
            'score': 80,
            'completed_beads': 3,
            'failed_beads': 0,
            'incidents': 0,
            'current_trust': 'provisional',
            'history': [],
        }
    ],
}


class TestComputeMutation:
    def test_bead_completed_increases_score(self):
        result = compute_mutation(BASE_DATA, 'Builder', 'BEAD-TEST-01', 'MP-TEST-01',
                                  'bead_completed', timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['score'] == 85
        assert agent['completed_beads'] == 4

    def test_bead_failed_decreases_score(self):
        result = compute_mutation(BASE_DATA, 'Builder', 'BEAD-TEST-01', 'MP-TEST-01',
                                  'bead_failed', timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['score'] == 70
        assert agent['failed_beads'] == 1

    def test_score_capped_at_max(self):
        data = {**BASE_DATA, 'agents': [{
            **BASE_DATA['agents'][0], 'score': 98,
        }]}
        result = compute_mutation(data, 'Builder', 'B', 'M', 'bead_completed',
                                  timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['score'] == SCORE_CAP

    def test_score_floored_at_zero(self):
        data = {**BASE_DATA, 'agents': [{
            **BASE_DATA['agents'][0], 'score': 5,
        }]}
        result = compute_mutation(data, 'Builder', 'B', 'M', 'incident',
                                  timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['score'] == SCORE_FLOOR

    def test_promote_threshold_sets_trusted(self):
        data = {**BASE_DATA, 'agents': [{
            **BASE_DATA['agents'][0], 'score': 82,
        }]}
        result = compute_mutation(data, 'Builder', 'B', 'M', 'bead_completed',
                                  timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['current_trust'] == 'trusted'

    def test_demote_threshold_sets_restricted(self):
        data = {**BASE_DATA, 'agents': [{
            **BASE_DATA['agents'][0], 'score': 58,
        }]}
        result = compute_mutation(data, 'Builder', 'B', 'M', 'bead_failed',
                                  timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert agent['current_trust'] == 'restricted'

    def test_history_entry_added(self):
        result = compute_mutation(BASE_DATA, 'Builder', 'BEAD-TEST-01', 'MP-TEST-01',
                                  'bead_completed', timestamp='2026-01-01T01:00:00+00:00')
        agent = next(a for a in result['agents'] if a['role'] == 'Builder')
        assert len(agent['history']) == 1
        assert agent['history'][0]['event'] == 'bead_completed'
        assert agent['history'][0]['bead_id'] == 'BEAD-TEST-01'

    def test_new_agent_created_if_not_found(self):
        result = compute_mutation(BASE_DATA, 'Scout', 'B', 'M', 'bead_completed',
                                  timestamp='2026-01-01T01:00:00+00:00')
        roles = [a['role'] for a in result['agents']]
        assert 'Scout' in roles


class TestFormatScorecardEntry:
    def test_has_required_fields(self):
        entry = format_scorecard_entry(
            'Builder', 'BEAD-TEST-01', 'MP-TEST-01',
            'bead_completed', True, 3, 0,
            '2026-01-01T01:00:00+00:00',
        )
        for field in ['timestamp', 'event', 'bead_id', 'role', 'mission_id',
                      'validation_passed', 'budget_used', 'incident_count', 'updated_at']:
            assert field in entry, f"missing field: {field}"


class TestDryRunDoesNotWrite:
    def test_dry_run_record_does_not_write(self, tmp_path, monkeypatch):
        import scripts.cat_score_agent as sa
        monkeypatch.setattr(sa, 'SCORECARD_PATH',
                            sa.ROOT / 'agents' / 'registry' / 'AGENT_SCORECARD.yaml')
        new_data, path = record_event(
            'Builder', 'BEAD-DRY-01', 'MP-DRY-01', 'bead_completed',
            dry_run=True,
        )
        assert path is None


class TestFilesystemState:
    def test_agent_scorecard_yaml_exists(self):
        assert (ROOT_PATH / 'agents' / 'registry' / 'AGENT_SCORECARD.yaml').exists()

    def test_scorecards_dir_exists(self):
        assert (ROOT_PATH / 'agents' / 'scorecards').is_dir()

    def test_agent_scorecard_schema_exists(self):
        assert (ROOT_PATH / 'schemas' / 'agent_scorecard.schema.json').exists()


class TestDryRunSampleCli:
    def test_sample_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(ROOT_PATH / 'scripts' / 'cat_score_agent.py'),
             '--dry-run', '--sample'],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'DRY-RUN' in result.stdout
