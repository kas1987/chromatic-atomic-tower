#!/usr/bin/env python3
"""comms_adapter.py — read-only interface stub for the Calendar/Email tool plane.

SCAFFOLD ONLY. Validates a Comms tool-plane descriptor and exposes the interface
a live adapter would implement, but performs NO email/calendar sends and NO
network I/O, and holds NO credentials. Any send/connect call raises
``ScaffoldError`` so the boundary is explicit and enforced.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / 'schemas' / 'tool_plane_comms.schema.json'


class ScaffoldError(RuntimeError):
    """Raised when a scaffold-only adapter is asked to perform live I/O."""


def validate_descriptor(descriptor: dict) -> list[str]:
    from jsonschema import Draft202012Validator
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    return [e.message for e in Draft202012Validator(schema).iter_errors(descriptor)]


class CommsAdapter:
    """Read-only interface over a validated Comms tool-plane descriptor."""

    def __init__(self, descriptor: dict) -> None:
        errors = validate_descriptor(descriptor)
        if errors:
            raise ValueError(f'invalid comms tool-plane descriptor: {errors[:3]}')
        self.descriptor = descriptor

    # --- read-only introspection (safe) ------------------------------------
    def describe(self) -> dict:
        return dict(self.descriptor)

    def channels(self) -> list[str]:
        return list(self.descriptor.get('channels', []))

    def is_read_only(self) -> bool:
        return self.descriptor.get('default_mode', 'read_only') == 'read_only'

    def supports(self, capability: str) -> bool:
        return capability in self.descriptor.get('capabilities', [])

    # --- live operations (intentionally unavailable in the scaffold) --------
    def connect(self):
        raise ScaffoldError('scaffold: no live comms connection (security gate deferred)')

    def send(self, _message: dict):
        raise ScaffoldError('scaffold: no live send (security gate deferred)')


def load_descriptor(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))
