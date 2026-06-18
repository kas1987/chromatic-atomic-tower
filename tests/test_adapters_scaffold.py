"""Coverage for the database tool-plane adapter and the shared load_descriptor
helpers (scripts/adapters/database_adapter.py, comms_adapter.py).

The comms adapter has dedicated tests in test_tool_plane_comms.py; this file
fills the database-adapter gap and covers the on-disk load_descriptor path for
both adapters.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import comms_adapter as ca
import database_adapter as da

ROOT = Path(__file__).resolve().parents[1]

DB_EXAMPLE = json.loads(
    (ROOT / "tests" / "fixtures" / "toolplanes" / "database_example.json").read_text(encoding="utf-8")
)
COMMS_EXAMPLE = json.loads(
    (ROOT / "tests" / "fixtures" / "toolplanes" / "comms_example.json").read_text(encoding="utf-8")
)


# ---------------------------------------------------------------------------
# database adapter introspection
# ---------------------------------------------------------------------------

def test_database_adapter_read_only_introspection():
    a = da.DatabaseAdapter(DB_EXAMPLE)
    assert a.is_read_only() is True
    assert a.describe()["plane"] == "database"
    assert isinstance(a.engines(), list)
    assert a.supports(DB_EXAMPLE["capabilities"][0]) is True
    assert a.supports("definitely-not-a-capability") is False


def test_database_adapter_rejects_invalid_descriptor():
    with pytest.raises(ValueError):
        da.DatabaseAdapter({"plane": "database"})


def test_database_adapter_has_no_live_io():
    a = da.DatabaseAdapter(DB_EXAMPLE)
    with pytest.raises(da.ScaffoldError):
        a.connect()
    with pytest.raises(da.ScaffoldError):
        a.query("SELECT 1")
    with pytest.raises(da.ScaffoldError):
        a.write("INSERT INTO t VALUES (1)")


# ---------------------------------------------------------------------------
# validate_descriptor (function form)
# ---------------------------------------------------------------------------

def test_database_validate_descriptor_ok_and_bad():
    assert da.validate_descriptor(DB_EXAMPLE) == []
    assert da.validate_descriptor({"plane": "database"})


def test_comms_validate_descriptor_ok_and_bad():
    assert ca.validate_descriptor(COMMS_EXAMPLE) == []
    assert ca.validate_descriptor({"plane": "comms"})


# ---------------------------------------------------------------------------
# load_descriptor (the previously-uncovered last line of each module)
# ---------------------------------------------------------------------------

def test_load_descriptor_database(tmp_path):
    p = tmp_path / "db.json"
    p.write_text(json.dumps(DB_EXAMPLE), encoding="utf-8")
    assert da.load_descriptor(p) == DB_EXAMPLE
    assert da.load_descriptor(str(p)) == DB_EXAMPLE


def test_load_descriptor_comms(tmp_path):
    p = tmp_path / "comms.json"
    p.write_text(json.dumps(COMMS_EXAMPLE), encoding="utf-8")
    assert ca.load_descriptor(p) == COMMS_EXAMPLE
