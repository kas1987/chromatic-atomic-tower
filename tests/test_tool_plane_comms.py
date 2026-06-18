"""Tests for the Calendar/Email (comms) tool plane (BEAD-CAT-A013-4C01-02).

Scaffold only: validates the descriptor schema and asserts the adapter performs
no live sends/I/O (connect/send raise ScaffoldError).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'adapters'))

import comms_adapter as ca

SCHEMA = json.loads((ROOT / 'schemas' / 'tool_plane_comms.schema.json').read_text(encoding='utf-8'))
EXAMPLE = json.loads((ROOT / 'tests' / 'fixtures' / 'toolplanes' / 'comms_example.json').read_text(encoding='utf-8'))


def test_schema_is_valid_metaschema():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_validates():
    assert list(Draft202012Validator(SCHEMA).iter_errors(EXAMPLE)) == []


def test_missing_required_fails():
    bad = {k: v for k, v in EXAMPLE.items() if k != 'channels'}
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_bad_channel_enum_fails():
    bad = dict(EXAMPLE, channels=['sms'])
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_no_additional_properties():
    bad = dict(EXAMPLE, smtp_password='hunter2')  # live credential must be rejected
    assert list(Draft202012Validator(SCHEMA).iter_errors(bad))


def test_adapter_read_only_introspection():
    a = ca.CommsAdapter(EXAMPLE)
    assert a.is_read_only() is True
    assert a.supports('read') is True
    assert 'email' in a.channels()
    assert a.describe()['plane'] == 'comms'


def test_adapter_rejects_invalid_descriptor():
    with pytest.raises(ValueError):
        ca.CommsAdapter({'plane': 'comms'})


def test_adapter_has_no_live_send():
    a = ca.CommsAdapter(EXAMPLE)
    for call in (a.connect, lambda: a.send({'to': 'x@y.z', 'body': 'hi'})):
        with pytest.raises(ca.ScaffoldError):
            call()
