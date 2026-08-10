"""A020-03 tests for bounded cross-repository mutation authorization."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

from scripts.cat_cross_repo_gate import evaluate_request


ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schemas" / "cross_repo_mutation.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def valid_request() -> dict:
    return {
        "contract_version": "1.0.0",
        "mission_id": "MP-CAT-A020-4C01",
        "bead_id": "BEAD-CAT-A020-4C01-03",
        "target_repo": "harness-v2",
        "operation": "write",
        "target_paths": [".cat/runtime/evidence.json"],
        "allowed_paths": [".cat/runtime/**"],
        "validation_command": "python -m pytest tests/test_runtime.py -q",
        "evidence_path": "evidence/a020/harness_v2_mutation.json",
        "rollback_reference": "revert commit or restore the target snapshot",
        "approved_by": "Human Owner",
        "requested_at": "2026-08-08T14:30:00Z",
    }


def test_schema_is_valid_and_accepts_complete_request():
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    validate(instance=valid_request(), schema=schema)


def test_schema_rejects_missing_trace_fields():
    request = valid_request()
    del request["mission_id"]
    del request["evidence_path"]
    with pytest.raises(ValidationError):
        validate(instance=request, schema=load_schema())


def test_gate_rejects_target_outside_declared_allowed_paths():
    request = valid_request()
    request["target_paths"] = ["src/unrelated.py"]
    result = evaluate_request(request)
    assert result["allowed"] is False
    assert any("allowed_paths" in error for error in result["errors"])


def test_gate_rejects_CAT_governance_paths():
    request = valid_request()
    request["target_paths"] = ["missions/registry/MISSION_REGISTRY.yaml"]
    request["allowed_paths"] = ["missions/**"]
    result = evaluate_request(request)
    assert result["allowed"] is False
    assert any("CAT-protected" in error for error in result["errors"])


def test_gate_rejects_CAT_governance_paths_with_windows_separators():
    request = valid_request()
    request["target_paths"] = [r"missions\registry\MISSION_REGISTRY.yaml"]
    request["allowed_paths"] = [r"missions\**"]
    result = evaluate_request(request)
    assert result["allowed"] is False
    assert any("CAT-protected" in error for error in result["errors"])


@pytest.mark.parametrize("evidence_path", ["evidence/../outside.md", r"evidence\..\outside.md"])
def test_schema_rejects_evidence_path_traversal(evidence_path):
    request = valid_request()
    request["evidence_path"] = evidence_path
    with pytest.raises(ValidationError):
        validate(instance=request, schema=load_schema())


def test_gate_rejects_missing_human_approval():
    request = valid_request()
    request["approved_by"] = ""
    result = evaluate_request(request)
    assert result["allowed"] is False
    assert any("approval" in error for error in result["errors"])


def test_authorized_request_returns_traceable_evidence_without_mutation():
    request = valid_request()
    before = copy.deepcopy(request)
    result = evaluate_request(request)
    assert result["allowed"] is True
    assert result["decision"] == "authorized"
    assert result["evidence"]["mission_id"] == request["mission_id"]
    assert result["evidence"]["bead_id"] == request["bead_id"]
    assert result["evidence"]["target_paths"] == request["target_paths"]
    assert result["evidence"]["validation_command"] == request["validation_command"]
    assert result["evidence"]["evidence_path"] == request["evidence_path"]
    assert request == before
