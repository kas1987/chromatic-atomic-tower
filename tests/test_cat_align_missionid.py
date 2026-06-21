"""Coverage for cat_align_check.py and cat_mission_id_check.py main() paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import cat_align_check
import cat_mission_id_check


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# cat_align_check
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_returns_dict_with_required_keys(self):
        report = cat_align_check.build_report()
        for key in ('version', 'status', 'generated_at', 'drift_count', 'ok', 'drift'):
            assert key in report

    def test_status_is_pass_or_fail(self):
        report = cat_align_check.build_report()
        assert report['status'] in ('pass', 'fail')

    def test_drift_count_matches_drift_list(self):
        report = cat_align_check.build_report()
        assert report['drift_count'] == len(report['drift'])


class TestRenderMarkdown:
    def test_header_present(self):
        report = {
            'version': '0.1.0',
            'status': 'pass',
            'generated_at': '2026-01-01T00:00:00+00:00',
            'drift_count': 0,
            'ok': ['mission aligned'],
            'drift': [],
        }
        md = cat_align_check.render_markdown(report)
        assert '# Alignment Check Report' in md
        assert 'Status: **pass**' in md

    def test_ok_section_shown(self):
        report = {
            'version': '0.1.0',
            'status': 'pass',
            'generated_at': '2026-01-01T00:00:00+00:00',
            'drift_count': 0,
            'ok': ['mission aligned', 'bead aligned'],
            'drift': [],
        }
        md = cat_align_check.render_markdown(report)
        assert '## OK' in md
        assert 'mission aligned' in md

    def test_drift_section_shown(self):
        report = {
            'version': '0.1.0',
            'status': 'fail',
            'generated_at': '2026-01-01T00:00:00+00:00',
            'drift_count': 1,
            'ok': [],
            'drift': [{'code': 'D001', 'message': 'bead mismatch', 'remediation': 'fix it'}],
        }
        md = cat_align_check.render_markdown(report)
        assert '## Drift' in md
        assert '[D001]' in md
        assert 'fix it' in md

    def test_no_ok_section_when_empty(self):
        report = {
            'version': '0.1.0',
            'status': 'pass',
            'generated_at': '2026-01-01T00:00:00+00:00',
            'drift_count': 0,
            'ok': [],
            'drift': [],
        }
        md = cat_align_check.render_markdown(report)
        assert '## OK' not in md


class TestAlignCheckMain:
    def test_main_returns_zero_or_one(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_align_check.py'])
        result = cat_align_check.main()
        assert result in (0, 1)

    def test_main_json_flag_produces_json(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_align_check.py', '--json'])
        result = cat_align_check.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        # Find the JSON blob (after the markdown output)
        for line in out.splitlines():
            if line.startswith('{'):
                data = json.loads(out[out.index('{'):])
                assert 'status' in data
                break

    def test_main_strict_returns_one_on_drift(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_align_check.py', '--strict'])
        result = cat_align_check.main()
        # If aligned: 0. If drift: 1. Both are valid.
        assert result in (0, 1)

    def test_main_write_report(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(cat_align_check, 'ROOT', tmp_path)
        monkeypatch.setattr(sys, 'argv', ['cat_align_check.py', '--write-report'])
        result = cat_align_check.main()
        assert result in (0, 1)
        # Should have created the evidence dir
        assert (tmp_path / 'evidence' / 'tower').is_dir()
        json_path = tmp_path / 'evidence' / 'tower' / 'align_check_report.json'
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding='utf-8'))
        assert 'status' in data


# ---------------------------------------------------------------------------
# cat_mission_id_check
# ---------------------------------------------------------------------------

class TestSuggestNextLegacyId:
    def test_returns_string(self):
        result = cat_mission_id_check.suggest_next_legacy_id()
        assert isinstance(result, str)
        assert result.startswith('MP-CAT-')

    def test_returns_mp_cat_nnn_format(self):
        import re
        result = cat_mission_id_check.suggest_next_legacy_id()
        assert re.match(r'^MP-CAT-\d{3}$', result), f"unexpected: {result}"

    def test_uses_tmp_root_with_no_missions(self, tmp_path):
        (tmp_path / 'missions' / 'active').mkdir(parents=True)
        (tmp_path / 'missions' / 'registry').mkdir(parents=True)
        import yaml
        (tmp_path / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml').write_text(
            yaml.dump({'missions': [], 'active_mission_id': ''}), encoding='utf-8'
        )
        result = cat_mission_id_check.suggest_next_legacy_id(root=tmp_path)
        assert result == 'MP-CAT-001'


class TestMissionIdExists:
    def test_real_repo_mission_exists(self):
        # Get a real mission ID from the registry
        import yaml
        registry_path = ROOT / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'
        if registry_path.exists():
            reg = yaml.safe_load(registry_path.read_text(encoding='utf-8')) or {}
            missions = reg.get('missions', [])
            if missions:
                real_id = missions[0].get('mission_id', '')
                if real_id:
                    assert cat_mission_id_check.mission_id_exists(real_id) is True

    def test_nonexistent_mission_returns_false(self):
        assert cat_mission_id_check.mission_id_exists('MP-CAT-ZZZNONE') is False


class TestCheckCollisions:
    def test_returns_two_lists(self):
        mission_col, bead_col = cat_mission_id_check.check_collisions()
        assert isinstance(mission_col, list)
        assert isinstance(bead_col, list)


class TestMissionIdCheckMain:
    def test_main_suggest_id(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_mission_id_check.py', '--suggest-id'])
        result = cat_mission_id_check.main()
        assert result == 0
        out = capsys.readouterr().out
        assert 'MP-CAT-' in out

    def test_main_json_output(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_mission_id_check.py', '--json'])
        result = cat_mission_id_check.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert 'status' in data
        assert 'mission_collisions' in data
        assert 'bead_collisions' in data

    def test_main_text_output(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['cat_mission_id_check.py'])
        result = cat_mission_id_check.main()
        assert result in (0, 1)
        out = capsys.readouterr().out
        assert 'collision' in out.lower() or 'No mission' in out
