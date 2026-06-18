"""Tests for schemas/intent_envelope.schema.json — Intent Envelope (GO-mode stage 1)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas' / 'intent_envelope.schema.json'
EXAMPLE_PATH = ROOT / 'tests' / 'fixtures' / 'intent' / 'intent_envelope_example.json'


@pytest.fixture(scope='module')
def schema():
    with SCHEMA_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope='module')
def example():
    with EXAMPLE_PATH.open() as f:
        return json.load(f)


def test_example_is_valid(schema, example):
    """The bundled example envelope must pass Draft 2020-12 validation."""
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_missing_required_field_fails(schema):
    """An instance missing a required field (raw_text) must fail validation."""
    instance = {
        "intent_id": "INT-CAT-0002",
        "timestamp": "2026-06-18T01:00:00Z",
        "source": "schedule",
        # raw_text is intentionally omitted
    }
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0, "Expected validation errors for missing required field"
    required_errors = [e for e in errors if e.validator == 'required']
    assert len(required_errors) > 0, "Expected a 'required' validation error"
    # jsonschema surfaces missing property name in the error message
    assert any('raw_text' in e.message for e in required_errors)


def test_invalid_source_enum_fails(schema):
    """An instance with an invalid source enum value must fail validation."""
    instance = {
        "intent_id": "INT-CAT-0003",
        "timestamp": "2026-06-18T02:00:00Z",
        "source": "webhook",  # not in enum
        "raw_text": "This source is not allowed.",
    }
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(instance))
    assert len(errors) > 0, "Expected validation errors for invalid source enum value"
    enum_errors = [e for e in errors if e.validator == 'enum']
    assert len(enum_errors) > 0, "Expected an 'enum' validation error for source field"
