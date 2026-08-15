"""Tests for scripts/cat_mission_package.py — read-only Mission Package assembler."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_mission_package
from jsonschema import Draft202012Validator

SCHEMA_PATH = ROOT / 'schemas' / 'mission_package.schema.json'


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def test_closed_mission_package_shape():
    """A fully closed mission (A011) has correct status, bead count, and kind."""
    record = cat_mission_package.build_package('MP-CAT-A011-4C01')
    assert record['mission_status'] == 'closed'
    assert record['bead_summary']['total'] == 4
    assert record['kind'] == 'mission_package'


def test_closed_mission_validates_against_schema():
    """The A011 package record must validate against mission_package.schema.json."""
    record = cat_mission_package.build_package('MP-CAT-A011-4C01')
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(record))
    assert errors == [], f'Schema violations: {[e.message for e in errors]}'


def test_unknown_mission_returns_empty_beads():
    """A non-existent mission ID returns an empty beads list and does not raise."""
    record = cat_mission_package.build_package('MP-CAT-DOES-NOT-EXIST')
    assert record['beads'] == []
    assert record['bead_summary']['total'] == 0


def test_unknown_mission_kind_is_mission_package():
    """Even for an unknown mission, kind is always 'mission_package'."""
    record = cat_mission_package.build_package('MP-CAT-DOES-NOT-EXIST')
    assert record['kind'] == 'mission_package'


def test_unknown_mission_validates_against_schema():
    """The unknown-mission record must still satisfy the schema."""
    record = cat_mission_package.build_package('MP-CAT-DOES-NOT-EXIST')
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(record))
    assert errors == [], f'Schema violations: {[e.message for e in errors]}'


def test_closed_mission_next_steps():
    """A closed mission reports next_steps == ['mission closed']."""
    record = cat_mission_package.build_package('MP-CAT-A011-4C01')
    assert record['next_steps'] == ['mission closed']


def test_record_has_required_keys():
    """build_package always returns all required top-level keys."""
    record = cat_mission_package.build_package('MP-CAT-A011-4C01')
    for key in ('kind', 'timestamp', 'mission_id', 'mission_title',
                'mission_status', 'beads', 'bead_summary',
                'evidence_refs', 'next_steps'):
        assert key in record, f'Missing key: {key}'
