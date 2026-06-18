#!/usr/bin/env python3
"""database_adapter.py — read-only interface stub for the Database tool plane.

SCAFFOLD ONLY. This adapter validates a Database tool-plane descriptor and
exposes the *interface* a live adapter would implement, but performs NO database
or network I/O and holds NO credentials. Any mutating/connecting call raises
``ScaffoldError`` so the boundary is explicit and enforced.

Live integration (real engines, connection_ref resolution, queries) belongs to a
separate, security-gated mission.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / 'schemas' / 'tool_plane_database.schema.json'


class ScaffoldError(RuntimeError):
    """Raised when a scaffold-only adapter is asked to perform live I/O."""


def validate_descriptor(descriptor: dict) -> list[str]:
    """Return a list of schema-validation error messages ([] means valid)."""
    from jsonschema import Draft202012Validator
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    return [e.message for e in Draft202012Validator(schema).iter_errors(descriptor)]


class DatabaseAdapter:
    """Read-only interface over a validated Database tool-plane descriptor."""

    def __init__(self, descriptor: dict) -> None:
        errors = validate_descriptor(descriptor)
        if errors:
            raise ValueError(f'invalid database tool-plane descriptor: {errors[:3]}')
        self.descriptor = descriptor

    # --- read-only introspection (safe) ------------------------------------
    def describe(self) -> dict:
        return dict(self.descriptor)

    def engines(self) -> list[str]:
        return list(self.descriptor.get('engines', []))

    def is_read_only(self) -> bool:
        return self.descriptor.get('default_mode', 'read_only') == 'read_only'

    def supports(self, capability: str) -> bool:
        return capability in self.descriptor.get('capabilities', [])

    # --- live operations (intentionally unavailable in the scaffold) --------
    def connect(self):
        raise ScaffoldError('scaffold: no live database connection (security gate deferred)')

    def query(self, _statement: str):
        raise ScaffoldError('scaffold: no live database query (security gate deferred)')

    def write(self, _statement: str):
        raise ScaffoldError('scaffold: no live database write (security gate deferred)')


def load_descriptor(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))
