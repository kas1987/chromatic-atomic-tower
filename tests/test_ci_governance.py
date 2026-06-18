import json

from scripts import cat_ci
from scripts.cat_ci import build_report, run_check, write_report
from scripts.common import ROOT, load_yaml, validate_with_schema


def test_ci_governance_rules_exist():
    rules = load_yaml(ROOT / 'gates/ci/CI_GOVERNANCE_RULES.yaml')
    assert rules['principle'] == 'No CI Pass = No Promotion'
    assert rules['pr_checks']['require_changed_file_scope'] is True


def test_ci_report_schema_for_status_only_run():
    report = build_report('test', include_pytest=False)
    assert report['status'] == 'passed'
    assert validate_with_schema(report, ROOT / 'schemas/ci_report.schema.json') == []


def test_run_check_passed():
    result = run_check('noop', ['python', '-c', 'print("hi")'])
    assert result['id'] == 'noop'
    assert result['status'] == 'passed'
    assert result['returncode'] == 0
    assert 'hi' in result['details']


def test_run_check_failed_captures_returncode():
    result = run_check('boom', ['python', '-c', 'import sys; sys.exit(3)'])
    assert result['status'] == 'failed'
    assert result['returncode'] == 3


def test_write_report_emits_summary_and_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_ci, 'ROOT', tmp_path)
    report = {
        'report_id': 'CAT-CI-TEST',
        'status': 'passed',
        'summary': {'passed': 2, 'failed': 0, 'skipped': 0},
        'checks': [
            {'id': 'a', 'status': 'passed', 'command': 'cmd-a'},
            {'id': 'b', 'status': 'passed', 'command': 'cmd-b'},
        ],
    }
    write_report(report)
    summary = tmp_path / 'evidence/ci/summaries/cat_ci_summary.json'
    md = tmp_path / 'evidence/ci/reports/cat_ci_report.md'
    assert json.loads(summary.read_text(encoding='utf-8'))['report_id'] == 'CAT-CI-TEST'
    body = md.read_text(encoding='utf-8')
    assert 'CAT-CI-TEST' in body
    assert '- a: passed' in body
