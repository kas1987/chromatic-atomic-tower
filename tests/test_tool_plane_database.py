"""Tests for the Database tool plane (BEAD-CAT-A013-4C01-01).

Scaffold only: validates the descriptor schema and asserts the adapter performs
no live I/O (mutating/connecting calls raise ScaffoldError).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'adapters'))

import database_adapter as dba

SCHEMA = json.loads((ROOT / 'schemas' / 'tool_plane_database.schema.json').read_text(encoding='utf-8'))
EXAMPLE = json.loads((ROOT / 'tests' / 'fixtures' / 'toolplanes' / 'database_example.json').read_text(encoding='utf-8'))


def test_schema_is_valid_metaschema():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_validates():
    assert list(Draft202012Validator(SCHEMA).iter_errors(EXAMPLE)) == []


def test_missing_required_fails():
    bad = {k: v for k, v in EXAMPLE.items() if k != 'engines'}
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_bad_engine_enum_fails():
    bad = dict(EXAMPLE, engines=['oracle'])
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_no_additional_properties():
    bad = dict(EXAMPLE, dsn='postgres://user:pw@host/db')  # live DSN must be rejected
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_adapter_read_only_introspection():
    a = dba.DatabaseAdapter(EXAMPLE)
    assert a.is_read_only() is True
    assert a.supports('read') is True
    assert 'sqlite' in a.engines()
    assert a.describe()['plane'] == 'database'


def test_adapter_rejects_invalid_descriptor():
    with pytest.raises(ValueError):
        dba.DatabaseAdapter({'plane': 'database'})  # missing required fields


def test_adapter_has_no_live_io():
    a = dba.DatabaseAdapter(EXAMPLE)
    for call in (a.connect, lambda: a.query('SELECT 1'), lambda: a.write('DELETE')):
        with pytest.raises(dba.ScaffoldError):
            call()
