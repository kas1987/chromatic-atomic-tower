"""Tests for the agent-approved gate (replaces the human approver).

The gate stays enforced (`human_gate_if_required`), but approval is recorded by
the configured `gate_approver_agent` (default Auditor) — an agent independent of
the Builder/Orchestrator that did the work — rather than a human.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cat_transition as ct


def test_gate_approver_agent_default_is_a_registered_role():
    agent = ct.gate_approver_agent()
    assert agent  # non-empty
    assert agent.lower() in ct._registry_roles(), f'{agent} must be a registered role'


def test_gate_not_required_passes():
    ok, msg = ct.evaluate_guard('human_gate_if_required', 'mission', {'human_gate': {'required': False}})
    assert ok is True
    assert 'not required' in msg


def test_required_gate_approved_by_agent_no_human():
    """A required gate passes via the agent approver — no human actor needed."""
    ok, msg = ct.evaluate_guard(
        'human_gate_if_required', 'mission',
        {'human_gate': {'required': True, 'approver': 'Human Owner'}},
        actor='',  # no human actor supplied
    )
    assert ok is True
    assert 'agent' in msg.lower()
    assert ct.gate_approver_agent().lower() in msg.lower()


def test_required_gate_fails_if_agent_not_registered(monkeypatch):
    """If the configured approver agent isn't a real role, the gate fails (No Gate = No Promotion)."""
    monkeypatch.setattr(ct, 'gate_approver_agent', lambda *a, **k: 'Nonexistent')
    ok, msg = ct.evaluate_guard(
        'human_gate_if_required', 'mission',
        {'human_gate': {'required': True}},
    )
    assert ok is False
    assert 'not a registered role' in msg
