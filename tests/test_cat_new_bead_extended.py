"""Extended tests for scripts/cat_new_bead.py.

Targets the uncovered lines 29-86 (main() and helpers).
All tests use 'import cat_new_bead' per the critical import pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

import cat_new_bead

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BEAD_TEMPLATE_CONTENT = {
    'bead_id': 'BEAD-CHANGE-ME',
    'mission_id': 'MP-CHANGE-ME',
    'title': 'Change me',
    'status': 'queued',
    'agent_role': 'Builder',
    'autonomy_level': 'L3',
    'objective': 'State one atomic objective.',
    'allowed_paths': ['path/**'],
    'forbidden_paths': ['.env'],
    'dependencies': [],
    'tool_budget': {
        'search': 1,
        'read': 4,
        'write': 2,
        'execute': 1,
        'max_runtime_minutes': 20,
    },
    'confidence': {
        'minimum': 75,
        'current': 75,
    },
    'risk_level': 'medium',
    'reversibility': 'high',
    'stop_conditions': ['Confidence drops below minimum.'],
    'definition_of_done': ['Objective complete.'],
    'validation': [
        {
            'type': 'self_review',
            'command': 'manual',
            'evidence_path': 'evidence/reports/CHANGE_ME.md',
            'required': True,
        }
    ],
    'required_output': ['summary'],
    'handoff': {'next_bead_id': None, 'notes': []},
}


def _write_bead_template(root: Path) -> None:
    """Create the BEAD template at the expected location under root."""
    tpl_dir = root / 'beads' / 'templates'
    tpl_dir.mkdir(parents=True, exist_ok=True)
    tpl_path = tpl_dir / 'BEAD_TEMPLATE.yaml'
    tpl_path.write_text(yaml.safe_dump(BEAD_TEMPLATE_CONTENT, sort_keys=False), encoding='utf-8')


def _run_main(monkeypatch, argv: list[str], root: Path) -> int:
    """Patch sys.argv + ROOT and call cat_new_bead.main(); return exit code."""
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(cat_new_bead, 'ROOT', root)
    return cat_new_bead.main()


# ---------------------------------------------------------------------------
# TestLegacyMissionNumber
# ---------------------------------------------------------------------------

class TestLegacyMissionNumber:
    def test_extracts_number_from_legacy_id(self):
        assert cat_new_bead._legacy_mission_number('MP-CAT-003') == 3

    def test_returns_none_for_new_format(self):
        assert cat_new_bead._legacy_mission_number('MP-CAT-A014-4C01') is None

    def test_returns_none_for_garbage(self):
        assert cat_new_bead._legacy_mission_number('NOT-A-MISSION') is None

    def test_zero_padded_number(self):
        assert cat_new_bead._legacy_mission_number('MP-CAT-005') == 5


# ---------------------------------------------------------------------------
# TestDeriveBead
# ---------------------------------------------------------------------------

class TestDeriveBead:
    def test_derives_from_new_format(self):
        result = cat_new_bead._derive_bead_id_from_mission('MP-CAT-A014-4C01', '03')
        assert result == 'BEAD-CAT-A014-4C01-03'

    def test_derives_from_legacy(self):
        result = cat_new_bead._derive_bead_id_from_mission('MP-CAT-005', '01')
        assert result == 'BEAD-CAT-005-01'


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_with_seq_creates_file(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        out_dir = tmp_path / 'beads' / 'active'
        argv = [
            'cat_new_bead.py',
            '--seq', '01',
            '--mission', 'MP-CAT-A014-4C01',
            '--title', 'Test Bead',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('BEAD-CAT-A014-4C01-01_*.yaml'))
        assert len(files) == 1

    def test_main_with_explicit_id(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        out_dir = tmp_path / 'beads' / 'active'
        argv = [
            'cat_new_bead.py',
            '--id', 'BEAD-CAT-A014-4C01-05',
            '--mission', 'MP-CAT-A014-4C01',
            '--title', 'Explicit ID Bead',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('BEAD-CAT-A014-4C01-05_*.yaml'))
        assert len(files) == 1

    def test_main_seq_and_id_are_mutually_exclusive(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        argv = [
            'cat_new_bead.py',
            '--seq', '01',
            '--id', 'BEAD-CAT-A014-4C01-01',
            '--mission', 'MP-CAT-A014-4C01',
            '--title', 'Conflict',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0

    def test_main_neither_seq_nor_id(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        argv = [
            'cat_new_bead.py',
            '--mission', 'MP-CAT-A014-4C01',
            '--title', 'No seq or id',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0

    def test_main_legacy_mission_above_cutoff(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        # MP-CAT-006 is >= cutoff (6), should error
        argv = [
            'cat_new_bead.py',
            '--mission', 'MP-CAT-006',
            '--seq', '01',
            '--title', 'X',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0

    def test_main_missing_required_mission(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        argv = [
            'cat_new_bead.py',
            '--seq', '01',
            '--title', 'No Mission',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0

    def test_main_invalid_seq_format(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        argv = [
            'cat_new_bead.py',
            '--seq', 'abc',
            '--mission', 'MP-CAT-A014-4C01',
            '--title', 'X',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0

    def test_main_output_file_has_correct_bead_id(self, monkeypatch, tmp_path):
        _write_bead_template(tmp_path)
        out_dir = tmp_path / 'beads' / 'active'
        argv = [
            'cat_new_bead.py',
            '--seq', '07',
            '--mission', 'MP-CAT-S001-4C01',
            '--title', 'My Bead',
            '--out', str(out_dir),
        ]
        rc = _run_main(monkeypatch, argv, tmp_path)
        assert rc == 0
        files = list(out_dir.glob('*.yaml'))
        assert len(files) == 1
        import yaml as _yaml
        data = _yaml.safe_load(files[0].read_text(encoding='utf-8'))
        assert data['bead_id'] == 'BEAD-CAT-S001-4C01-07'
        assert data['mission_id'] == 'MP-CAT-S001-4C01'
        assert data['title'] == 'My Bead'

    def test_main_seq_requires_new_format_mission(self, monkeypatch, tmp_path):
        """--seq with a legacy mission ID (not new-format) should fail."""
        _write_bead_template(tmp_path)
        # MP-CAT-003 is legacy and below cutoff, but --seq requires new format
        argv = [
            'cat_new_bead.py',
            '--seq', '01',
            '--mission', 'MP-CAT-003',
            '--title', 'Legacy seq fail',
        ]
        monkeypatch.setattr(sys, 'argv', argv)
        monkeypatch.setattr(cat_new_bead, 'ROOT', tmp_path)
        with pytest.raises(SystemExit) as exc:
            cat_new_bead.main()
        assert exc.value.code != 0
