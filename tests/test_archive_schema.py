#!/usr/bin/env python3
"""Test archive schema validation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from common import ROOT, load_yaml, validate_with_schema

SCHEMA_PATH = ROOT / 'schemas/archive.schema.json'
VALID_FIXTURE = ROOT / 'tests/fixtures/archive/valid_archive_record.json'
INVALID_FIXTURE = ROOT / 'tests/fixtures/archive/invalid_archive_record.json'


def test_archive_schema_exists():
    """Archive schema file must exist."""
    assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"


def test_archive_schema_valid_json():
    """Archive schema must be valid JSON."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    assert isinstance(schema, dict)
    assert '$schema' in schema
    assert 'properties' in schema
    assert 'required' in schema


def test_valid_archive_record_passes():
    """Valid archive record must pass validation."""
    with open(VALID_FIXTURE) as f:
        record = json.load(f)
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    errors = validate_with_schema(record, schema)
    assert not errors, f"Valid record failed: {errors}"


def test_invalid_archive_record_fails():
    """Invalid archive record must fail validation."""
    with open(INVALID_FIXTURE) as f:
        record = json.load(f)
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    errors = validate_with_schema(record, schema)
    assert errors, "Invalid record should have failed validation"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
