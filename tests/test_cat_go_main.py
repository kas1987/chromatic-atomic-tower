"""Coverage for cat_go.py and cat_go_run.py main() paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import cat_go
import cat_go_run


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# cat_go.main()
# ---------------------------------------------------------------------------

class TestCatGoMain:
    def test_main_returns_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go.py'])
        result = cat_go.main()
        assert result == 0

    def test_main_json_flag_produces_json(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go.py', '--json'])
        result = cat_go.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert 'stages' in data
        assert 'bead_count' in data

    def test_main_json_record_has_required_keys(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go.py', '--json'])
        cat_go.main()
        out = capsys.readouterr().out
        data = json.loads(out)
        for key in ('stages_total', 'stages_satisfied', 'bead_count'):
            assert key in data

    def test_main_text_output_has_stages(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go.py'])
        cat_go.main()
        out = capsys.readouterr().out
        # Should print stage info
        assert 'GO' in out or any(s in out for s in cat_go.STAGES)

    def test_main_emit_flag_writes_file(self, monkeypatch, tmp_path, capsys):
        evidence_dir = tmp_path / 'evidence' / 'go'
        monkeypatch.setattr(cat_go, 'EVIDENCE_DIR', evidence_dir)
        monkeypatch.setattr(sys, 'argv', ['cat_go.py', '--emit'])
        result = cat_go.main()
        assert result == 0
        # Check a file was written
        files = list(evidence_dir.glob('*.json'))
        assert len(files) >= 1
        data = json.loads(files[0].read_text(encoding='utf-8'))
        assert 'stages' in data

    def test_main_with_explicit_mission(self, monkeypatch, capsys):
        # Use a mission from the real tower or an empty string fallback
        import yaml
        tower_path = ROOT / 'state' / 'TOWER_STATE.yaml'
        mission_id = ''
        if tower_path.exists():
            tower = yaml.safe_load(tower_path.read_text(encoding='utf-8')) or {}
            mission_id = tower.get('active_mission_id', '')
        if not mission_id:
            pytest.skip("No active mission in tower state")
        monkeypatch.setattr(sys, 'argv', ['cat_go.py', '--mission', mission_id, '--json'])
        result = cat_go.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data.get('mission_id') == mission_id


# ---------------------------------------------------------------------------
# cat_go_run.main()
# ---------------------------------------------------------------------------

class TestCatGoRunMain:
    def test_main_dry_run_json_returns_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--dry-run', '--json'])
        result = cat_go_run.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['kind'] == 'go_run_action'
        assert data['dry_run'] is True

    def test_main_dry_run_json_has_action(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--json'])
        result = cat_go_run.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert 'action' in data
        assert 'automatable' in data['action']

    def test_main_dry_run_text_output(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py'])
        result = cat_go_run.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'GO-run orchestrator' in out
        assert '[DRY-RUN]' in out

    def test_main_dry_run_prints_stages(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py'])
        cat_go_run.main()
        out = capsys.readouterr().out
        # Should print each stage
        for stage in cat_go.STAGES:
            assert stage in out

    def test_main_execute_not_automatable_returns_zero(self, monkeypatch, capsys):
        # When action is not automatable, --execute prints recommendation and returns 0
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--execute'])
        # mock plan_action to return non-automatable
        monkeypatch.setattr(cat_go_run, 'plan_action', lambda rec: {
            'next_stage': 'intent',
            'action': 'review intent doc',
            'automatable': False,
            'kind': 'manual',
            'reason': 'manual review needed',
        })
        result = cat_go_run.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'Not automatable' in out or 'Recommended' in out

    def test_main_execute_check_kind_calls_subprocess(self, monkeypatch, capsys, tmp_path):
        # When kind='check' and automatable=True, calls subprocess.run for cat_validate.py
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(cat_go_run, 'plan_action', lambda rec: {
            'next_stage': 'score_validate',
            'action': 'run cat_validate.py --all',
            'automatable': True,
            'kind': 'check',
            'reason': 'run validation',
        })
        monkeypatch.setattr('cat_go_run.subprocess.run', mock_run)
        monkeypatch.setattr(cat_go_run, 'EVIDENCE_DIR', tmp_path / 'evidence' / 'go')
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--execute'])
        result = cat_go_run.main()
        assert mock_run.called
        assert result == 0

    def test_main_execute_mutate_kind_calls_closeout(self, monkeypatch, capsys, tmp_path):
        # When kind='mutate' and automatable=True, calls cat_sprint_closeout.py
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(cat_go_run, 'plan_action', lambda rec: {
            'next_stage': 'continue_close',
            'action': 'run cat_sprint_closeout.py',
            'automatable': True,
            'kind': 'mutate',
            'reason': 'all stages satisfied',
        })
        monkeypatch.setattr('cat_go_run.subprocess.run', mock_run)
        monkeypatch.setattr(cat_go_run, 'EVIDENCE_DIR', tmp_path / 'evidence' / 'go')
        # get a valid mission_id
        import yaml
        tower_path = ROOT / 'state' / 'TOWER_STATE.yaml'
        mission_id = 'MP-TEST-001'
        if tower_path.exists():
            tower = yaml.safe_load(tower_path.read_text(encoding='utf-8')) or {}
            mission_id = tower.get('active_mission_id', 'MP-TEST-001') or 'MP-TEST-001'
        monkeypatch.setattr(cat_go_run, '_active_mission_id', lambda: mission_id)
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--execute'])
        result = cat_go_run.main()
        assert mock_run.called
        assert result == 0

    def test_main_execute_else_kind_prints_recommendation(self, monkeypatch, capsys, tmp_path):
        monkeypatch.setattr(cat_go_run, 'plan_action', lambda rec: {
            'next_stage': 'intent',
            'action': 'review intent documentation',
            'automatable': True,
            'kind': 'other',  # unknown kind → else branch
            'reason': 'other',
        })
        monkeypatch.setattr(cat_go_run, 'EVIDENCE_DIR', tmp_path / 'evidence' / 'go')
        monkeypatch.setattr(sys, 'argv', ['cat_go_run.py', '--execute'])
        result = cat_go_run.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'Recommended' in out
