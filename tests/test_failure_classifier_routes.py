"""Branch coverage for scripts/cat_classify_failure.py routing logic.

The existing test_failure_classifier.py covers two routes; this file exercises
every keyword route, the unknown-failure fallback, keyword precedence, and that
every route in ROUTES yields a schema-valid result.
"""
from __future__ import annotations

import pytest

from scripts.cat_classify_failure import ROUTES, classify, infer_failure_type
from scripts.common import ROOT, validate_with_schema

SCHEMA = ROOT / "schemas" / "ci_failure.schema.json"


@pytest.mark.parametrize("check,message,expected", [
    ("scan", "secret token leaked", "security_failure"),
    ("scope", "wrote outside allowed paths", "scope_failure"),
    ("evidence", "missing evidence bundle", "evidence_failure"),
    ("state", "illegal state transition", "state_failure"),
    ("schema", "required property missing", "schema_failure"),
    ("tests", "pytest assertion failed", "test_failure"),
    ("misc", "something inexplicable", "unknown_failure"),
])
def test_infer_failure_type_routes(check, message, expected):
    assert infer_failure_type(check, message) == expected


def test_keyword_precedence_security_first():
    # message hits both security ('secret') and test ('pytest') keywords;
    # security is checked first so it wins.
    assert infer_failure_type("ci", "pytest found a secret") == "security_failure"


def test_unknown_failure_requires_human_gate():
    result = classify("weird", "no known keywords here")
    assert result["failure_type"] == "unknown_failure"
    assert result["human_gate_required"] is True


@pytest.mark.parametrize("failure_type", list(ROUTES.keys()))
def test_every_route_is_schema_valid(failure_type):
    # Build a message guaranteed to map to this failure_type by using its own
    # name as a token where possible, then assert classify output validates.
    sample = {
        "schema_failure": ("c", "schema validation failed"),
        "state_failure": ("c", "state transition error"),
        "evidence_failure": ("c", "evidence bundle missing"),
        "test_failure": ("c", "pytest failed"),
        "security_failure": ("c", "secret found"),
        "scope_failure": ("c", "outside allowed scope"),
        "unknown_failure": ("c", "totally opaque"),
    }[failure_type]
    result = classify(*sample)
    assert result["failure_type"] == failure_type
    assert validate_with_schema(result, SCHEMA) == []
