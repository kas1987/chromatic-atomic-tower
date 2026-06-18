"""Tests for agents/registry/TOOL_REGISTRY.yaml — governed tool plane registry."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'schemas'
REGISTRY = ROOT / 'agents' / 'registry' / 'TOOL_REGISTRY.yaml'

_VALID_STATUSES = {"implemented", "scaffolded", "planned"}


def _load_registry() -> dict:
    with open(REGISTRY, encoding='utf-8') as fh:
        return yaml.safe_load(fh)


def _load_schema() -> dict:
    with open(SCHEMAS / 'tool_registry.schema.json', encoding='utf-8') as fh:
        return json.load(fh)


def test_registry_validates_against_schema():
    """TOOL_REGISTRY.yaml must pass Draft202012Validator with no errors."""
    data = _load_registry()
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    assert errors == [], f"Schema validation errors: {errors}"


def test_registry_has_at_least_9_planes():
    """planes list must contain at least 9 entries."""
    data = _load_registry()
    planes = data.get('planes', [])
    assert len(planes) >= 9, f"Expected >= 9 planes, got {len(planes)}"


def test_plane_ids_include_database_and_comms():
    """database and comms plane ids must be present."""
    data = _load_registry()
    plane_ids = {p['plane'] for p in data.get('planes', [])}
    assert 'database' in plane_ids, "Missing plane id: database"
    assert 'comms' in plane_ids, "Missing plane id: comms"


def test_every_plane_status_in_enum():
    """Every plane's status must be one of: implemented, scaffolded, planned."""
    data = _load_registry()
    for plane in data.get('planes', []):
        status = plane.get('status')
        assert status in _VALID_STATUSES, (
            f"Plane '{plane.get('plane')}' has invalid status '{status}'"
        )
