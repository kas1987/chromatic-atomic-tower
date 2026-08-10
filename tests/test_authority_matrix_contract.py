"""Task-relative proof for the A020 canonical authority matrix."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "authority_matrix.schema.json"


def load_matrix() -> tuple[dict, dict]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    matrix = schema["examples"][0]
    return schema, matrix


def validate_unique_writers(matrix: dict) -> None:
    facts = [entry["fact"] for entry in matrix["entries"]]
    if len(facts) != len(set(facts)):
        raise ValueError("each mutable fact must have exactly one matrix entry")


def test_schema_is_valid_and_embedded_matrix_conforms() -> None:
    schema, matrix = load_matrix()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(matrix))
    assert errors == []
    validate_unique_writers(matrix)


def test_duplicate_fact_is_rejected() -> None:
    _, matrix = load_matrix()
    duplicate = json.loads(json.dumps(matrix))
    duplicate["entries"].append(duplicate["entries"][0])
    with pytest.raises(ValueError, match="exactly one"):
        validate_unique_writers(duplicate)


def test_runtime_and_project_consumers_are_not_cat_writers() -> None:
    _, matrix = load_matrix()
    for entry in matrix["entries"]:
        if entry["canonical_owner"] != "CAT":
            assert entry["write_policy"] in {
                "LOCAL_ONLY",
                "RUNTIME_EVIDENCE_ONLY",
            }
