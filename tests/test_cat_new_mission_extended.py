"""Extended tests for scripts/cat_new_mission.py.

Targets the uncovered lines 24-59 (main() and supporting branches).
All tests use 'import cat_new_mission' per the critical import pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

import cat_new_mission

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

M1_BASIC_TEMPLATE_CONTENT = {
    'mission_id': 'MP-CHANGE-ME',
    'title': 'Change me',
    'level': 'M1',
    'status': 'draft',
    'owner': 'Human Owner',
    'priority': 4,
    'risk_level': 'low',
    'reversibility': 'high',
    'autonomy_level': 'L2',
    'confidence_minimum': 70,
    'created': 'YYYY-MM-DD',
    'last_updated': 'YYYY-MM-DD',
    'objective': 'Describe the mission objective in one clear sentence.',
    'background': 'Explain why this mission exists and what context matters.',
    'scope': {'in': ['Change me'], 'out': ['Change me']},
    'allowed_paths': ['path/**'],
    'forbidden_paths': ['.env'],
    'dependencies': [],
    'acceptance_criteria': ['Change me'],
    'success_metrics': ['Change me'],
    'required_validation': [
        {
            'type': 'self_review',
            'command': 'manual',
            'evidence_path': 'evidence/reports/CHANGE_ME.md',
            'required': True,
        }
    ],
    'rollback': {'required': False, 'plan': 'Change me'},
    'human_gate': {'required': False, 'approver': 'Human Owner'},
    'tool_budget': {
        'search': 0,
        'read': 2,
        'write': 2,
        'execute': 0,
        'max_runtime_minutes': 15,
    },
    'beads': [],
    'evidence_requirements': ['Change me'],
    'notes': [],
}


def _write_mission_templates(root: Path) -> None:
    """Create all four mission templates at the expected location under root."""
    tpl_dir = root / 'missions' / 'templates'
    tpl_dir.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(M1_BASIC_TEMPLATE_CONTENT, sort_keys=False)
    for name in ('M1_BASIC', 'M2_INTERMEDIATE', 'M3_COMPLEX', 'M4_ATOMIC'):
        (tpl_dir / f'{name}.yaml').write_text(content, encoding='utf-8')


def _run_main(monkeypatch, argv: list[str], root: Path) -> int:
    """Patch sys.argv + ROOT and call cat_new_mission.main(); return exit code."""
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(cat_new_mission, 'ROOT', root)
    return cat_new_mission.main()


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_creates_mission_file(self, monkeypatch, tmp_path):
        _write_mission_templates(tmp_path)
        out_dir = tmp_path / 'missions' / 'backlog'
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-A099-4C01',
            '--title', 'Test Mission',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('MP-CAT-A099-4C01_*.yaml'))
        assert len(files) == 1

    def test_main_legacy_id_creates_file(self, monkeypatch, tmp_path):
        """Legacy IDs below cutoff with --allow-legacy-id should succeed."""
        _write_mission_templates(tmp_path)
        out_dir = tmp_path / 'missions' / 'backlog'
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-001',
            '--title', 'Test Legacy',
            '--allow-legacy-id',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('MP-CAT-001_*.yaml'))
        assert len(files) == 1

    def test_main_missing_id(self, monkeypatch, tmp_path):
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--title', 'No ID',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_missing_title(self, monkeypatch, tmp_path):
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-A099-4C01',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_missing_template(self, monkeypatch, tmp_path):
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--id', 'MP-CAT-A099-4C01',
            '--title', 'No Template',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_output_file_has_correct_fields(self, monkeypatch, tmp_path):
        _write_mission_templates(tmp_path)
        out_dir = tmp_path / 'missions' / 'backlog'
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-B002-2C01',
            '--title', 'My Mission',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('*.yaml'))
        assert len(files) == 1
        data = yaml.safe_load(files[0].read_text(encoding='utf-8'))
        assert data['mission_id'] == 'MP-CAT-B002-2C01'
        assert data['title'] == 'My Mission'

    def test_main_legacy_above_cutoff_fails(self, monkeypatch, tmp_path):
        """Legacy IDs at or above cutoff (MP-CAT-006) must fail even with --allow-legacy-id."""
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-006',
            '--title', 'Too High',
            '--allow-legacy-id',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_invalid_id_without_allow_legacy(self, monkeypatch, tmp_path):
        """A plain legacy ID without --allow-legacy-id must fail."""
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-003',
            '--title', 'Legacy No Flag',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_invalid_id_format_without_allow_legacy(self, monkeypatch, tmp_path):
        """A completely invalid ID without --allow-legacy-id should fail."""
        _write_mission_templates(tmp_path)
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'INVALID-FORMAT',
            '--title', 'Bad ID',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_mission, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_mission.main()
        assert exc.value.code != 0

    def test_main_example_id_allowed_with_allow_legacy(self, monkeypatch, tmp_path):
        """EXAMPLE-style IDs are accepted when --allow-legacy-id is passed."""
        _write_mission_templates(tmp_path)
        out_dir = tmp_path / 'missions' / 'backlog'
        argv = [
            'cat_new_mission.py',
            '--template', 'M1_BASIC',
            '--id', 'MP-CAT-EXAMPLE-DEMO-1',
            '--title', 'Example Mission',
            '--allow-legacy-id',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('MP-CAT-EXAMPLE-DEMO-1_*.yaml'))
        assert len(files) == 1
