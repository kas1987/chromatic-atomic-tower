from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.common import ROOT, validate_with_schema

ROUTE_SCHEMA = ROOT / "schemas" / "route_decision.schema.json"
EVENT_SCHEMA = ROOT / "schemas" / "lifecycle_event.schema.json"
POLICY_PATH = ROOT / "gates" / "ROUTE_DECISION_POLICY.yaml"
HEAD = "a" * 40
ARTIFACT_HEAD = "b" * 40


def policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def digest_policy() -> str:
    return hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()


def decision(case: dict, decision_id: str = "0123456789abcdef0123456789abcdef") -> dict:
    constraints = {
        "head_match": True,
        "output_valid": True,
        "budget_available": True,
        "provider_available": True,
        "fields_consistent": True,
        "dependency_cycle_free": True,
        "duplicate_delivery": False,
    }
    constraints.update(case.get("constraints", {}))
    if not constraints["head_match"]:
        outcome, effect, reason = "block", "none", "stale head"
    elif not constraints["output_valid"]:
        outcome, effect, reason = "block", "none", "malformed output"
    elif not constraints["dependency_cycle_free"]:
        outcome, effect, reason = "block", "none", "dependency cycle"
    elif not constraints["fields_consistent"]:
        outcome, effect, reason = "require_human", "none", "conflicting fields"
    elif case.get("policy_digest_valid") is False:
        outcome, effect, reason = "require_human", "none", "policy drift"
    elif not constraints["budget_available"]:
        outcome, effect, reason = "require_human", "none", "budget exhausted"
    elif not constraints["provider_available"]:
        outcome, effect, reason = "require_human", "none", "provider outage"
    elif constraints["duplicate_delivery"]:
        outcome, effect, reason = "allow_plan", "none", "duplicate replay"
    elif case.get("hitl_mode") in {"approval_required", "human_only"}:
        outcome, effect, reason = "require_human", "none", "human gate"
    else:
        outcome, effect, reason = "allow_plan", "dry_run", "safe plan"
    return {
        "schema_version": "1.0.0",
        "decision_id": decision_id,
        "subject": {"type": "bead", "id": "BEAD-CAT-A023-4C01-06"},
        "expected_revision": "rev-07",
        "observed_head_sha": HEAD,
        "artifact_head_sha": ARTIFACT_HEAD,
        "lifecycle_state": "active",
        "classification": {
            "priority": 1,
            "severity": "high",
            "complexity": "M4",
            "risk_level": "high",
            "hitl_mode": case.get("hitl_mode", "review_required"),
        },
        "constraints": constraints,
        "policy": {"policy_id": policy()["policy_id"], "policy_version": policy()["version"], "policy_digest": digest_policy()},
        "outcome": outcome,
        "effect": effect,
        "evidence": {"refs": ["evidence/reports/routing/fixture.json"], "observed_head_sha": HEAD, "artifact_head_sha": ARTIFACT_HEAD},
        "rationale": reason,
    }


def event_for(route: dict, event_id: str = "fedcba9876543210fedcba9876543210") -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": event_id,
        "idempotency_key": f"{route['subject']['id']}:{route['expected_revision']}:{route['decision_id']}",
        "subject": route["subject"],
        "prior_revision": route["expected_revision"],
        "applied_outcome": route["outcome"],
        "effect": route["effect"],
        "policy": route["policy"],
        "head": {"observed_head_sha": route["observed_head_sha"], "artifact_head_sha": route["artifact_head_sha"]},
        "evidence_refs": route["evidence"]["refs"],
        "actor_type": "agent",
    }


@pytest.mark.parametrize(
    ("name", "case", "expected"),
    [
        ("safe", {}, ("allow_plan", "dry_run")),
        ("stale head", {"constraints": {"head_match": False}}, ("block", "none")),
        ("malformed output", {"constraints": {"output_valid": False}}, ("block", "none")),
        ("exhausted budget", {"constraints": {"budget_available": False}}, ("require_human", "none")),
        ("provider outage", {"constraints": {"provider_available": False}}, ("require_human", "none")),
        ("conflicting fields", {"constraints": {"fields_consistent": False}}, ("require_human", "none")),
        ("dependency cycle", {"constraints": {"dependency_cycle_free": False}}, ("block", "none")),
        ("policy drift", {"policy_digest_valid": False}, ("require_human", "none")),
        ("human approval", {"hitl_mode": "approval_required"}, ("require_human", "none")),
    ],
)
def test_route_matrix_is_deterministic_and_fail_closed(name, case, expected):
    result = decision(case)
    assert (result["outcome"], result["effect"]) == expected, name
    assert validate_with_schema(result, ROUTE_SCHEMA) == []


def test_contract_separates_lifecycle_state_and_classification():
    result = decision({})
    assert result["lifecycle_state"] == "active"
    assert result["classification"]["complexity"] == "M4"
    assert result["lifecycle_state"] != result["classification"]["complexity"]


def test_duplicate_delivery_returns_original_without_mutation():
    original = decision({})
    replay = decision({"constraints": {"duplicate_delivery": True}}, original["decision_id"])
    assert replay["decision_id"] == original["decision_id"]
    assert replay["outcome"] == original["outcome"]
    assert replay["effect"] == "none"
    assert original["effect"] == "dry_run"


def test_lifecycle_event_is_schema_valid_and_idempotent():
    route = decision({"constraints": {"budget_available": False}})
    event = event_for(route)
    assert validate_with_schema(event, EVENT_SCHEMA) == []
    replay = deepcopy(event)
    assert replay["idempotency_key"] == event["idempotency_key"]
    assert replay == event


def test_policy_allows_only_contract_outcomes_and_effects():
    current = policy()
    assert set(current["allowed_outcomes"]) == {"allow_plan", "require_human", "block"}
    assert set(current["allowed_effects"]) == {"none", "dry_run"}
    for rule in current["rules"].values():
        assert rule["outcome"] in current["allowed_outcomes"]
        assert rule["effect"] in current["allowed_effects"]


def test_policy_precedence_is_explicit_and_unique():
    precedence = policy()["precedence"]
    assert len(precedence) == len(set(precedence))
    assert precedence[:3] == ["stale_head", "malformed_output", "dependency_cycle"]


@pytest.mark.parametrize("bad_field", ["observed_head_sha", "artifact_head_sha"])
def test_head_binding_is_required(bad_field):
    result = decision({})
    result.pop(bad_field)
    assert validate_with_schema(result, ROUTE_SCHEMA)


def test_event_cannot_claim_mutating_effect():
    event = event_for(decision({}))
    event["effect"] = "merge"
    assert validate_with_schema(event, EVENT_SCHEMA)
