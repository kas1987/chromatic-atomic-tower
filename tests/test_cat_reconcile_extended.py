"""Extended tests for cat_reconcile.py — targets the ~46% uncovered paths.

Covers:
- check() active mission match / mismatch
- check() required mission status wrong or missing from registry
- check() roadmap term present / missing
- check() no conditions (trivially passes)
- write_reports() creates both files, JSON is valid, MD has PASS and Missing section
- main() with and without --write-report (no crash)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

import cat_reconcile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_root(tmp_path: Path, registry: dict, roadmap_text: str = '') -> Path:
    """Populate a minimal tmp root with registry + roadmap."""
    reg_dir = tmp_path / 'missions' / 'registry'
    reg_dir.mkdir(parents=True)
    (reg_dir / 'MISSION_REGISTRY.yaml').write_text(yaml.dump(registry), encoding='utf-8')
    if roadmap_text:
        (tmp_path / 'CAT_ROADMAP.md').write_text(roadmap_text, encoding='utf-8')
    return tmp_path


def _make_target(tmp_path: Path, target: dict, name: str = 'target.yaml') -> Path:
    p = tmp_path / name
    p.write_text(yaml.dump(target), encoding='utf-8')
    return p


def _minimal_registry(active_id: str = 'MP-CAT-A001', missions: list | None = None) -> dict:
    return {
        'active_mission_id': active_id,
        'missions': missions or [
            {'mission_id': 'MP-CAT-A001', 'status': 'in_progress'},
        ],
    }


def _sample_report(status: str = 'passed', missing: list | None = None) -> dict:
    return {
        'report_id': 'CAT-RECONCILIATION-A009',
        'generated_at': '2026-01-01T00:00:00Z',
        'status': status,
        'active_mission_id': 'MP-CAT-A014-4C01',
        'next_mission_id': None,
        'checks': [{'name': 'active_matches', 'passed': True, 'details': 'ok'}],
        'missing': missing or [],
        'recommendations': [],
    }


# ---------------------------------------------------------------------------
# TestCheck
# ---------------------------------------------------------------------------

class TestCheck:
    def test_active_mission_matches(self, tmp_path):
        root = _make_root(tmp_path, _minimal_registry('MP-CAT-A001'))
        target = _make_target(tmp_path, {'canonical_active_mission_id': 'MP-CAT-A001'})
        result = cat_reconcile.check(target, root)
        assert result['status'] == 'passed'

    def test_active_mission_mismatch(self, tmp_path):
        root = _make_root(tmp_path, _minimal_registry('MP-CAT-A001'))
        target = _make_target(tmp_path, {'canonical_active_mission_id': 'MP-CAT-X999'})
        result = cat_reconcile.check(target, root)
        assert result['status'] == 'failed'
        # The check details should reference the mismatched ids
        active_check = next(
            c for c in result['checks'] if c['name'] == 'active_mission_matches_target'
        )
        assert not active_check['passed']

    def test_required_mission_wrong_status(self, tmp_path):
        registry = _minimal_registry(
            'MP-CAT-A001',
            missions=[{'mission_id': 'MP-CAT-A001', 'status': 'in_progress'}],
        )
        root = _make_root(tmp_path, registry)
        target = _make_target(
            tmp_path,
            {'required_missions': {'MP-CAT-A001': 'closed'}},
        )
        result = cat_reconcile.check(target, root)
        assert result['status'] == 'failed'
        status_check = next(
            c for c in result['checks'] if 'MP-CAT-A001' in c['name']
        )
        assert not status_check['passed']

    def test_required_mission_missing_from_registry(self, tmp_path):
        root = _make_root(tmp_path, _minimal_registry())
        target = _make_target(
            tmp_path,
            {'required_missions': {'MP-CAT-MISSING': 'in_progress'}},
        )
        result = cat_reconcile.check(target, root)
        assert 'MP-CAT-MISSING' in result['missing']

    def test_roadmap_term_present(self, tmp_path):
        root = _make_root(
            tmp_path,
            _minimal_registry(),
            roadmap_text='# CAT Roadmap\n\nBEAD-CAT-001 some text\n',
        )
        target = _make_target(
            tmp_path,
            {'required_roadmap_terms': ['BEAD-CAT-001']},
        )
        result = cat_reconcile.check(target, root)
        term_check = next(c for c in result['checks'] if 'BEAD-CAT-001' in c['name'])
        assert term_check['passed']

    def test_roadmap_term_missing(self, tmp_path):
        # No CAT_ROADMAP.md at all — roadmap is empty string, term won't be found
        root = _make_root(tmp_path, _minimal_registry())
        target = _make_target(
            tmp_path,
            {'required_roadmap_terms': ['BEAD-CAT-NOTHERE']},
        )
        result = cat_reconcile.check(target, root)
        assert result['status'] == 'failed'
        assert any('roadmap term' in m for m in result['missing'])

    def test_no_target_conditions(self, tmp_path):
        root = _make_root(tmp_path, _minimal_registry())
        target = _make_target(tmp_path, {})
        result = cat_reconcile.check(target, root)
        assert result['status'] == 'passed'


# ---------------------------------------------------------------------------
# TestWriteReports
# ---------------------------------------------------------------------------

class TestWriteReports:
    def test_creates_json_and_md(self, tmp_path):
        cat_reconcile.write_reports(_sample_report(), tmp_path)
        assert (tmp_path / 'evidence/reconciliation/reconciliation_report.json').exists()
        assert (tmp_path / 'evidence/reconciliation/reconciliation_report.md').exists()

    def test_json_content_is_valid(self, tmp_path):
        cat_reconcile.write_reports(_sample_report(), tmp_path)
        raw = (tmp_path / 'evidence/reconciliation/reconciliation_report.json').read_text(encoding='utf-8')
        parsed = json.loads(raw)
        assert parsed['report_id'] == 'CAT-RECONCILIATION-A009'

    def test_md_has_pass_status(self, tmp_path):
        cat_reconcile.write_reports(_sample_report(status='passed'), tmp_path)
        md = (tmp_path / 'evidence/reconciliation/reconciliation_report.md').read_text(encoding='utf-8')
        assert 'PASS' in md

    def test_md_has_missing_section(self, tmp_path):
        cat_reconcile.write_reports(
            _sample_report(status='failed', missing=['MP-CAT-X001', 'roadmap term: BEAD-X']),
            tmp_path,
        )
        md = (tmp_path / 'evidence/reconciliation/reconciliation_report.md').read_text(encoding='utf-8')
        assert '## Missing' in md
        assert 'MP-CAT-X001' in md


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_with_write_report(self, tmp_path, monkeypatch):
        # Build a minimal repo root in tmp_path
        registry = _minimal_registry()
        root = _make_root(tmp_path, registry)
        target_path = tmp_path / 'docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml'
        target_path.parent.mkdir(parents=True)
        target_path.write_text(yaml.dump({}), encoding='utf-8')

        monkeypatch.setattr(cat_reconcile, 'ROOT', root)
        monkeypatch.setattr(
            sys, 'argv',
            ['cat_reconcile.py', '--write-report'],
        )
        rc = cat_reconcile.main()
        assert rc in (0, 1)

    def test_main_no_write_report(self, tmp_path, monkeypatch):
        registry = _minimal_registry()
        root = _make_root(tmp_path, registry)
        target_path = tmp_path / 'docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml'
        target_path.parent.mkdir(parents=True)
        target_path.write_text(yaml.dump({}), encoding='utf-8')

        monkeypatch.setattr(cat_reconcile, 'ROOT', root)
        monkeypatch.setattr(sys, 'argv', ['cat_reconcile.py'])
        rc = cat_reconcile.main()
        assert rc in (0, 1)
