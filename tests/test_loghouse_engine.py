"""
Tests for LOGHOUSE normalizer and correlator (BEAD-03).
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.common import ROOT
from scripts.loghouse.normalize import normalize_batch, normalize_envelope, normalize_deploy_event
from scripts.loghouse.correlate import correlate, CorrelationWindow

FIXTURES = ROOT / "tests" / "fixtures" / "loghouse"


def test_normalize_envelope_valid():
    raw = {
        "event_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "ts": "2026-06-17T12:05:00Z",
        "signal_type": "log",
        "service": "payments-api",
        "env": "prod",
        "severity": "error",
        "message": "timeout",
        "commit_sha": "abc1234",
        "deploy_id": "deploy-20260617-1200",
        "attrs": {},
    }
    record, errors = normalize_envelope(raw)
    assert errors == []
    assert record is not None
    assert record["service"] == "payments-api"
    assert record["signal_type"] == "log"


def test_normalize_envelope_rejects_missing_required():
    raw = {
        "ts": "2026-06-17T12:05:00Z",
        "signal_type": "log",
        "severity": "info",
        "message": "missing service/env/etc",
        "attrs": {},
    }
    record, errors = normalize_envelope(raw)
    assert record is None
    assert len(errors) > 0


def test_normalize_envelope_rejects_invalid_env():
    raw = {
        "ts": "2026-06-17T12:05:00Z",
        "signal_type": "log",
        "service": "svc",
        "env": "production",  # invalid
        "severity": "info",
        "message": "x",
        "commit_sha": "abc1234",
        "deploy_id": "d-1",
        "attrs": {},
    }
    record, errors = normalize_envelope(raw)
    assert record is None
    assert len(errors) > 0


def test_normalize_deploy_event_valid():
    raw = {
        "deploy_id": "deploy-20260617-1200",
        "service": "payments-api",
        "commit_sha": "abc1234",
        "actor": "github-actions",
        "started_at": "2026-06-17T11:59:00Z",
        "completed_at": "2026-06-17T12:01:00Z",
        "status": "succeeded",
    }
    record, errors = normalize_deploy_event(raw)
    assert errors == []
    assert record is not None
    assert record["deploy_id"] == "deploy-20260617-1200"


def test_normalize_batch_from_fixture():
    fixture = json.loads((FIXTURES / "raw_signals.json").read_text())
    envelopes, deploy_events, rejected = normalize_batch(fixture)

    expected = json.loads((FIXTURES / "expected_normalized.json").read_text())

    assert len(envelopes) == expected["envelope_count"]
    assert len(deploy_events) == expected["deploy_event_count"]
    assert len(rejected) == expected["rejected_count"]
    assert envelopes[0]["service"] == expected["first_envelope_service"]
    assert envelopes[0]["env"] == expected["first_envelope_env"]
    assert deploy_events[0]["deploy_id"] == expected["deploy_event_deploy_id"]


def test_correlate_groups_by_deploy_context():
    envelopes = [
        {
            "event_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "ts": "2026-06-17T12:05:00Z",
            "signal_type": "log",
            "service": "payments-api",
            "env": "prod",
            "severity": "error",
            "message": "timeout",
            "commit_sha": "abc1234",
            "deploy_id": "deploy-20260617-1200",
            "attrs": {},
        },
        {
            "event_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "ts": "2026-06-17T12:06:00Z",
            "signal_type": "log",
            "service": "payments-api",
            "env": "prod",
            "severity": "error",
            "message": "error 2",
            "commit_sha": "abc1234",
            "deploy_id": "deploy-20260617-1200",
            "attrs": {},
        },
    ]
    deploy_events = [
        {
            "deploy_id": "deploy-20260617-1200",
            "service": "payments-api",
            "commit_sha": "abc1234",
            "actor": "ci",
            "started_at": "2026-06-17T11:59:00Z",
            "completed_at": "2026-06-17T12:01:00Z",
            "status": "succeeded",
        }
    ]

    windows = correlate(envelopes, deploy_events)
    assert len(windows) == 1
    window = windows[0]
    assert isinstance(window, CorrelationWindow)
    assert window.service == "payments-api"
    assert window.error_count() == 2
    assert window.has_deploy_event()


def test_correlate_separates_different_services():
    envelopes = [
        {
            "event_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "ts": "2026-06-17T12:05:00Z",
            "signal_type": "log",
            "service": "svc-a",
            "env": "prod",
            "severity": "info",
            "message": "ok",
            "commit_sha": "abc1234",
            "deploy_id": "d-1",
            "attrs": {},
        },
        {
            "event_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "ts": "2026-06-17T12:06:00Z",
            "signal_type": "log",
            "service": "svc-b",
            "env": "prod",
            "severity": "info",
            "message": "ok",
            "commit_sha": "def5678",
            "deploy_id": "d-2",
            "attrs": {},
        },
    ]
    windows = correlate(envelopes, [])
    assert len(windows) == 2
    services = {w.service for w in windows}
    assert services == {"svc-a", "svc-b"}
