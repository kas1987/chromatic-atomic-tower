from pathlib import Path
import json

import yaml

ROOT = Path(__file__).resolve().parents[1]

MISSION = 'missions/archived/MP-CAT-A006-4C01_HARNESS_ENGINEERING_ALIGNMENT.yaml'


def load_yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text(encoding='utf-8'))


def test_mission_references_all_beads():
    mission = load_yaml(MISSION)
    beads = {b['bead_id'] for b in mission['beads']}
    for idx in range(1, 9):
        assert f'BEAD-CAT-A006-4C01-0{idx}' in beads


def test_assertion_gates_include_core_gates():
    gates = load_yaml('gates/assertion_gates.yaml')['gates']
    gate_ids = {gate['gate_id'] for gate in gates}
    assert 'completeness_gate' in gate_ids
    assert 'substantive_validation_gate' in gate_ids
    assert 'control_validation_gate' in gate_ids
    assert 'evidence_sufficiency_gate' in gate_ids
    assert 'promotion_gate' in gate_ids


def test_complexity_routing_has_four_routes_and_fallbacks():
    routing = load_yaml('agents/model_routes.yaml')['complexity_routing']
    assert len(routing['default_routes']) >= 4
    assert routing['fallback_rules']
    assert routing['non_negotiables']


def test_skill_registry_has_skills():
    registry = load_yaml('agents/skills/SKILL_REGISTRY.yaml')
    assert registry['skills']
    assert all('skill_id' in s and 'owner_agent' in s for s in registry['skills'])


def test_json_schemas_parse():
    for rel in [
        'schemas/gate_result.schema.json',
        'schemas/assertion_evidence_map.schema.json',
        'schemas/model_routing_policy.schema.json',
        'schemas/skill_registry.schema.json',
    ]:
        data = json.loads((ROOT / rel).read_text(encoding='utf-8'))
        assert data['$schema']
        assert data['type'] == 'object'


def test_mermaid_docs_exist():
    text = (ROOT / 'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md').read_text(encoding='utf-8')
    assert text.count('```mermaid') >= 5
