"""Tests for scripts/cat_tool_budget_tracker.py — tool budget tracker."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import cat_tool_budget_tracker as tbt


@pytest.fixture()
def bead_file(tmp_path) -> Path:
    bead = {
        'bead_id': 'BEAD-CAT-TEST-01',
        'mission_id': 'MP-CAT-TEST',
        'title': 'Test BEAD',
        'status': 'active',
        'agent_role': 'Builder',
        'autonomy_level': 'L2',
        'objective': 'Test tool budget tracking.',
        'allowed_paths': ['scripts/**'],
        'forbidden_paths': ['.env'],
        'tool_budget': {
            'search': 2,
            'read': 8,
            'write': 4,
            'execute': 3,
            'max_runtime_minutes': 30,
        },
        'confidence': {'minimum': 80, 'current': 85, 'objective_clarity': 85,
                       'scope_clarity': 85, 'evidence_quality': 85,
                       'reversibility': 85, 'tool_fit': 85,
                       'risk_awareness': 85, 'testability': 85},
        'risk_level': 'low',
        'reversibility': 'high',
        'stop_conditions': ['Forbidden path touched.'],
        'definition_of_done': ['Tests pass.'],
        'validation': [],
        'required_output': ['output'],
        'handoff': {'from': 'Orchestrator', 'to': 'Builder', 'reviewer': 'Human Owner', 'next_bead_id': None},
    }
    p = tmp_path / 'BEAD-CAT-TEST-01.yaml'
    p.write_text(yaml.safe_dump(bead, sort_keys=False), encoding='utf-8')
    return p


@pytest.fixture()
def actual_within(tmp_path) -> Path:
    usage = {'search': 1, 'read': 4, 'write': 2, 'execute': 1}
    p = tmp_path / 'actual.json'
    p.write_text(json.dumps(usage), encoding='utf-8')
    return p


@pytest.fixture()
def actual_exceeded(tmp_path) -> Path:
    usage = {'search': 5, 'read': 10, 'write': 2, 'execute': 1}
    p = tmp_path / 'actual_exceeded.json'
    p.write_text(json.dumps(usage), encoding='utf-8')
    return p


class TestComputeUsage:
    def test_no_actual_all_ok(self, bead_file):
        bead = yaml.safe_load(bead_file.read_text())
        report = tbt.compute_usage(bead, {})
        assert report['status'] == 'ok'
        assert report['exceeded'] == []
        for cat in report['categories']:
            assert cat['used'] == 0

    def test_within_budget_ok(self, bead_file, actual_within):
        bead = yaml.safe_load(bead_file.read_text())
        actual = tbt._load_actual(actual_within)
        report = tbt.compute_usage(bead, actual)
        assert report['status'] == 'ok'
        assert report['exceeded'] == []

    def test_over_budget_detected(self, bead_file, actual_exceeded):
        bead = yaml.safe_load(bead_file.read_text())
        actual = tbt._load_actual(actual_exceeded)
        report = tbt.compute_usage(bead, actual)
        assert report['status'] == 'exceeded'
        assert 'search' in report['exceeded']
        assert 'read' in report['exceeded']

    def test_percentage_correct(self, bead_file, actual_within):
        bead = yaml.safe_load(bead_file.read_text())
        actual = tbt._load_actual(actual_within)
        report = tbt.compute_usage(bead, actual)
        search_cat = next(c for c in report['categories'] if c['category'] == 'search')
        assert search_cat['pct'] == 50.0
        assert search_cat['used'] == 1
        assert search_cat['limit'] == 2


class TestCmdCheck:
    def test_check_within_exits_0(self, bead_file, actual_within):
        import argparse
        args = argparse.Namespace(bead=str(bead_file), actual=str(actual_within))
        rc = tbt.cmd_check(args)
        assert rc == 0

    def test_check_exceeded_exits_1(self, bead_file, actual_exceeded):
        import argparse
        args = argparse.Namespace(bead=str(bead_file), actual=str(actual_exceeded))
        rc = tbt.cmd_check(args)
        assert rc == 1

    def test_check_no_actual_exits_0(self, bead_file):
        import argparse
        args = argparse.Namespace(bead=str(bead_file), actual=None)
        rc = tbt.cmd_check(args)
        assert rc == 0


class TestCmdSummarize:
    def test_summarize_text_output(self, bead_file, actual_within, capsys):
        import argparse
        args = argparse.Namespace(
            bead=str(bead_file), actual=str(actual_within),
            output=None, json=False,
        )
        rc = tbt.cmd_summarize(args)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'BEAD-CAT-TEST-01' in out
        assert 'search' in out

    def test_summarize_json_output(self, bead_file, actual_within, capsys):
        import argparse
        args = argparse.Namespace(
            bead=str(bead_file), actual=str(actual_within),
            output=None, json=True,
        )
        rc = tbt.cmd_summarize(args)
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed['bead_id'] == 'BEAD-CAT-TEST-01'
        assert 'categories' in parsed

    def test_summarize_writes_output_file(self, bead_file, actual_within, tmp_path):
        import argparse
        out_path = tmp_path / 'report.json'
        args = argparse.Namespace(
            bead=str(bead_file), actual=str(actual_within),
            output=str(out_path), json=False,
        )
        rc = tbt.cmd_summarize(args)
        assert rc == 0
        assert out_path.exists()
        parsed = json.loads(out_path.read_text())
        assert parsed['bead_id'] == 'BEAD-CAT-TEST-01'

    def test_missing_bead_file_exits(self, tmp_path):
        import argparse
        args = argparse.Namespace(
            bead=str(tmp_path / 'no_such.yaml'), actual=None,
            output=None, json=False,
        )
        with pytest.raises(SystemExit) as exc:
            tbt.cmd_summarize(args)
        assert exc.value.code == 1
