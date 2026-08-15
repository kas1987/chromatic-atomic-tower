from pathlib import Path

from scripts.common import ROOT, load_yaml, validate_with_schema


def test_active_mission_validates():
    """When sprint is idle, validate the latest archived mission contract instead."""
    archived = ROOT / 'missions/archived/MP-CAT-A007-4C01_LOGHOUSE_INTELLIGENCE.yaml'
    active_dir = ROOT / 'missions/active'
    if archived.is_file():
        mission_path = archived
    else:
        active_missions = sorted(active_dir.glob('MP-CAT-*.yaml'))
        assert active_missions, 'expected at least one mission contract in active/ or archived A007'
        mission_path = active_missions[0]
    mission = load_yaml(mission_path)
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_archived_mission_validates():
    mission = load_yaml(ROOT / 'missions/archived/MP-CAT-000_ESTABLISH_CORE.yaml')
    errors = validate_with_schema(mission, ROOT / 'schemas/mission.schema.json')
    assert errors == []


def test_example_bead_validates():
    bead = load_yaml(ROOT / 'beads/examples/BEAD-CAT-EXAMPLE-001.yaml')
    errors = validate_with_schema(bead, ROOT / 'schemas/bead.schema.json')
    assert errors == []


def test_go_resolver_script_exists():
    assert (ROOT / 'scripts/cat_resolve_go.py').is_file()
