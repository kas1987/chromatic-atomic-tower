from scripts.cat_ci import build_report
from scripts.common import ROOT, load_yaml, validate_with_schema


def test_ci_governance_rules_exist():
    rules = load_yaml(ROOT / 'gates/ci/CI_GOVERNANCE_RULES.yaml')
    assert rules['principle'] == 'No CI Pass = No Promotion'
    assert rules['pr_checks']['require_changed_file_scope'] is True


def test_ci_report_schema_for_status_only_run():
    report = build_report('test', include_pytest=False)
    assert report['status'] == 'passed'
    assert validate_with_schema(report, ROOT / 'schemas/ci_report.schema.json') == []
