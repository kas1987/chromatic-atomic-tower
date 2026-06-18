"""Tests for schemas/handoff_packet.schema.json — G-3 Handoff Packet schema."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "handoff_packet.schema.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "handoff" / "handoff_packet_example.json"


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def example(schema):
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data


def test_example_is_valid(schema, example):
    """The canonical fixture validates against the schema without errors."""
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_missing_bead_id_fails(schema):
    """A packet missing required field bead_id must fail validation."""
    packet = {
        "packet_id": "HOP-CAT-A011-02",
        "timestamp": "2026-06-18T01:00:00Z",
        "from_role": "Scout",
        "to_role": "Builder",
        # bead_id intentionally omitted
    }
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(packet))
    assert errors, "Expected validation errors for missing bead_id, but got none"
    error_messages = " ".join(str(e.message) for e in errors)
    assert "bead_id" in error_messages


def test_invalid_from_role_fails(schema):
    """A packet with from_role 'Architect' (not a valid enum value) must fail."""
    packet = {
        "packet_id": "HOP-CAT-A011-03",
        "timestamp": "2026-06-18T02:00:00Z",
        "from_role": "Architect",
        "to_role": "Reviewer",
        "bead_id": "BEAD-CAT-A011-4C01-02",
    }
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(packet))
    assert errors, "Expected validation errors for invalid from_role enum, but got none"
    error_messages = " ".join(str(e.message) for e in errors)
    assert "Architect" in error_messages
