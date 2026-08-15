"""Coverage for cat_stats.py and cat_self_heal.py."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

# Import via module object so monkeypatch.setattr targets the same namespace
# that the functions look up globals in.
import cat_stats
import cat_self_heal


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# cat_stats helpers
# ---------------------------------------------------------------------------

class TestCountByStatus:
    def test_empty_list(self):
        assert cat_stats._count_by_status([]) == {}

    def test_single_item(self):
        assert cat_stats._count_by_status([{'status': 'closed'}]) == {'closed': 1}

    def test_multiple_statuses(self):
        items = [
            {'status': 'closed'},
            {'status': 'approved'},
            {'status': 'closed'},
        ]
        counts = cat_stats._count_by_status(items)
        assert counts['closed'] == 2
        assert counts['approved'] == 1

    def test_skips_none_status(self):
        items = [{'status': None}, {'status': 'active'}]
        counts = cat_stats._count_by_status(items)
        assert None not in counts
        assert counts['active'] == 1

    def test_skips_missing_status_key(self):
        items = [{'title': 'no status'}, {'status': 'ok'}]
        counts = cat_stats._count_by_status(items)
        assert counts == {'ok': 1}


class TestRepoRoot:
    def test_returns_string(self):
        r = cat_stats._repo_root()
        assert isinstance(r, str)
        assert Path(r).is_dir()


class TestSummarize:
    def test_real_repo_has_missions(self):
        s = cat_stats.summarize()
        assert s['total_missions'] > 0
        assert isinstance(s['missions_by_status'], dict)
        assert isinstance(s['total_active_beads'], int)

    def test_summarize_has_all_keys(self):
        s = cat_stats.summarize()
        for key in ('total_missions', 'missions_by_status', 'active_mission_id',
                    'total_active_beads', 'beads_by_status'):
            assert key in s

    def test_raises_on_missing_registry(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cat_stats, '_missions_path', lambda: str(tmp_path / 'no_such.yaml'))
        with pytest.raises(FileNotFoundError):
            cat_stats.summarize()

    def test_beads_dir_not_found_returns_zero_beads(self, monkeypatch, tmp_path):
        registry_path = tmp_path / 'MISSION_REGISTRY.yaml'
        registry_path.write_text(yaml.dump({'missions': [], 'active_mission_id': ''}), encoding='utf-8')
        monkeypatch.setattr(cat_stats, '_missions_path', lambda: str(registry_path))
        monkeypatch.setattr(cat_stats, '_beads_dir', lambda: str(tmp_path / 'beads' / 'active'))
        s = cat_stats.summarize()
        assert s['total_active_beads'] == 0

    def test_malformed_bead_yaml_skipped(self, monkeypatch, tmp_path):
        registry_path = tmp_path / 'MISSION_REGISTRY.yaml'
        registry_path.write_text(yaml.dump({'missions': [], 'active_mission_id': ''}), encoding='utf-8')
        beads_dir = tmp_path / 'beads' / 'active'
        beads_dir.mkdir(parents=True)
        (beads_dir / 'bad.yaml').write_text(': invalid: yaml: [', encoding='utf-8')
        good_bead = {'bead_id': 'B-001', 'status': 'active'}
        (beads_dir / 'good.yaml').write_text(yaml.dump(good_bead), encoding='utf-8')
        monkeypatch.setattr(cat_stats, '_missions_path', lambda: str(registry_path))
        monkeypatch.setattr(cat_stats, '_beads_dir', lambda: str(beads_dir))
        s = cat_stats.summarize()
        assert s['total_active_beads'] == 1


class TestStatsMain:
    def test_main_returns_zero(self, capsys):
        result = cat_stats.main([])
        assert result == 0

    def test_main_json_flag(self, capsys):
        result = cat_stats.main(['--json'])
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert 'total_missions' in data

    def test_main_text_output(self, capsys):
        result = cat_stats.main([])
        assert result == 0
        out = capsys.readouterr().out
        assert 'Total missions' in out
        assert 'Active mission ID' in out

    def test_main_returns_one_on_missing_registry(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(cat_stats, '_missions_path', lambda: str(tmp_path / 'no_such.yaml'))
        result = cat_stats.main([])
        assert result == 1


# ---------------------------------------------------------------------------
# cat_self_heal
# ---------------------------------------------------------------------------

class TestBuildPlan:
    def test_returns_list(self):
        plan = cat_self_heal.build_plan()
        assert isinstance(plan, list)

    def test_all_actions_have_required_keys(self):
        plan = cat_self_heal.build_plan()
        for action in plan:
            assert 'repair_class' in action
            assert 'path' in action
            assert 'safe' in action

    def test_all_actions_marked_safe(self):
        plan = cat_self_heal.build_plan()
        for action in plan:
            assert action['safe'] is True

    def test_no_forbidden_paths_in_plan(self):
        plan = cat_self_heal.build_plan()
        forbidden = ['.env', 'secrets/', 'infra/prod/', 'production/', 'deploy/']
        for action in plan:
            for marker in forbidden:
                assert marker not in action['path']


class TestApplyPlan:
    def test_creates_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
        actions = [
            {
                'repair_class': 'create_missing_required_directory',
                'path': 'evidence/ci',
                'safe': True,
                'description': 'Create evidence/ci',
            }
        ]
        cat_self_heal.apply_plan(actions)
        assert (tmp_path / 'evidence' / 'ci').is_dir()

    def test_creates_gitkeep(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
        target_dir = tmp_path / 'evidence' / 'ci'
        target_dir.mkdir(parents=True)
        actions = [
            {
                'repair_class': 'create_gitkeep_placeholder',
                'path': 'evidence/ci/.gitkeep',
                'safe': True,
                'description': 'Create placeholder',
            }
        ]
        cat_self_heal.apply_plan(actions)
        assert (target_dir / '.gitkeep').exists()

    def test_skips_unsafe_actions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
        actions = [
            {
                'repair_class': 'create_missing_required_directory',
                'path': 'should_not_create',
                'safe': False,
                'description': 'Unsafe action',
            }
        ]
        cat_self_heal.apply_plan(actions)
        assert not (tmp_path / 'should_not_create').exists()

    def test_skips_forbidden_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cat_self_heal, 'ROOT', tmp_path)
        actions = [
            {
                'repair_class': 'create_missing_required_directory',
                'path': 'secrets/mydir',
                'safe': True,
                'description': 'Should be blocked by forbidden marker',
            }
        ]
        cat_self_heal.apply_plan(actions)
        assert not (tmp_path / 'secrets' / 'mydir').exists()


class TestSelfHealMain:
    def test_dry_run_returns_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_self_heal.py', '--dry-run'])
        result = cat_self_heal.main()
        assert result == 0

    def test_dry_run_json_output(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_self_heal.py', '--dry-run', '--json'])
        result = cat_self_heal.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['mode'] == 'dry-run'
        assert 'actions' in data

    def test_apply_returns_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_self_heal.py', '--apply'])
        result = cat_self_heal.main()
        assert result == 0

    def test_apply_json_output(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_self_heal.py', '--apply', '--json'])
        result = cat_self_heal.main()
        assert result == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['mode'] == 'apply'

    def test_text_output_has_header(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_self_heal.py', '--dry-run'])
        cat_self_heal.main()
        out = capsys.readouterr().out
        assert 'Self-Healing' in out or 'Mode' in out
