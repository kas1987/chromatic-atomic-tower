"""A020-04 tests for the generated-state ownership DAG guard."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

from scripts.cat_state_ownership_guard import validate_ownership


ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schemas" / "derived_state_ownership.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def valid_graph() -> dict:
    return {
        "contract_version": "1.0.0",
        "facts": [
            {
                "fact_id": "cat_derived_state",
                "canonical_writer": "CAT",
                "canonical_path": "state/TOWER_STATE.yaml",
                "derived_artifacts": [
                    {
                        "path": "state/SPRINT_STATE.md",
                        "writer": "CAT",
                        "source_fact": "cat_derived_state",
                    },
                    {
                        "path": "state/AGENT_HANDOFF_QUEUE.md",
                        "writer": "CAT",
                        "source_fact": "cat_derived_state",
                    },
                ],
                "consumers": ["Human Owner", "CAT agents"],
            }
        ],
    }


def test_schema_is_valid_and_accepts_canonical_to_derived_graph():
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    validate(instance=valid_graph(), schema=schema)


def test_guard_accepts_valid_graph_and_returns_evidence():
    result = validate_ownership(valid_graph())
    assert result["valid"] is True
    assert result["evidence"]["status"] == "valid"
    assert result["evidence"]["derived_artifact_count"] == 2


def test_guard_rejects_duplicate_fact_ids():
    graph = valid_graph()
    graph["facts"].append(copy.deepcopy(graph["facts"][0]))
    result = validate_ownership(graph)
    assert result["valid"] is False
    assert any("duplicate fact_id" in error for error in result["errors"])


def test_guard_rejects_conflicting_canonical_writers():
    graph = valid_graph()
    graph["facts"].append({
        "fact_id": "same_path_different_writer",
        "canonical_writer": "Harness V2",
        "canonical_path": "state/TOWER_STATE.yaml",
        "derived_artifacts": [],
        "consumers": ["CAT"],
    })
    result = validate_ownership(graph)
    assert result["valid"] is False
    assert any("conflicting writers" in error for error in result["errors"])


def test_guard_rejects_duplicate_canonical_path_even_with_same_writer():
    graph = valid_graph()
    graph["facts"].append({
        "fact_id": "duplicate_path",
        "canonical_writer": "CAT",
        "canonical_path": "state/TOWER_STATE.yaml",
        "derived_artifacts": [],
        "consumers": ["CAT"],
    })
    result = validate_ownership(graph)
    assert result["valid"] is False
    assert any("duplicate canonical path" in error for error in result["errors"])


def test_guard_rejects_derived_artifact_with_second_writer():
    graph = valid_graph()
    graph["facts"][0]["derived_artifacts"][0]["writer"] = "Harness V2"
    result = validate_ownership(graph)
    assert result["valid"] is False
    assert any("derived writer" in error for error in result["errors"])


def test_guard_rejects_unknown_source_fact_without_choosing_a_writer():
    graph = valid_graph()
    graph["facts"][0]["derived_artifacts"][0]["source_fact"] = "missing_fact"
    result = validate_ownership(graph)
    assert result["valid"] is False
    assert any("source_fact" in error for error in result["errors"])
