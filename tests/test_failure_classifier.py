from scripts.cat_classify_failure import classify
from scripts.common import ROOT, validate_with_schema


def test_classifies_schema_failure_and_validates_schema():
    result = classify('schema', 'schema validation failed')
    assert result['failure_type'] == 'schema_failure'
    assert result['self_heal_allowed'] is True
    assert validate_with_schema(result, ROOT / 'schemas/ci_failure.schema.json') == []


def test_classifies_security_as_human_gate():
    result = classify('secret scan', 'credential found in .env')
    assert result['failure_type'] == 'security_failure'
    assert result['human_gate_required'] is True
    assert result['self_heal_allowed'] is False
