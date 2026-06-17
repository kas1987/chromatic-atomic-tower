from pathlib import Path

from scripts.common import ROOT, load_yaml, validate_with_schema


def test_active_mission_validates():
    mission = load_yaml(ROOT / 'missions/active/MP-CAT-000_ESTABLISH_CORE.yaml')
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_active_bead_validates():
    bead = load_yaml(ROOT / 'beads/active/BEAD-CAT-000-001.yaml')
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors == []


def test_go_resolver_script_exists():
    assert (ROOT / 'scripts/cat_resolve_go.py').is_file()
