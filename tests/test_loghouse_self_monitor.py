"""
Tests for LOGHOUSE self-observability:
- cat_adapter.py mapping functions
- 4 new CAT governance rules
- --mode self end-to-end (clean signals → no findings)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

import sys
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.loghouse.cat_adapter import (
    _adapt_transitions,
    _adapt_closeouts,
    _adapt_go_decisions,
    _adapt_agent_runs,
)
from scripts.loghouse.normalize import normalize_batch
from scripts.loghouse.correlate import correlate
from scripts.loghouse.rules import (
    evaluate_windows,
    rule_bead_stuck_in_state,
    rule_go_block_frequency,
    rule_closeout_rejection_spike,
    rule_confidence_below_threshold,
    CAT_SERVICE,
)
from scripts.loghouse.correlate import CorrelationWindow

# ─── helpers ──────────────────────────────────────────────────────────────────

_COMMIT = "a6aec4f"
_SPRINT = "SPRINT-008"
_ENV = "local"


def _ts(offset_hours: float = 0.0) -> str:
    t = datetime.now(timezone.utc) - timedelta(hours=offset_hours)
    return t.isoformat()


def _make_window(envelopes: list[dict]) -> CorrelationWindow:
    w = CorrelationWindow(
        service=CAT_SERVICE,
        env=_ENV,
        commit_sha=_COMMIT,
        deploy_id=_SPRINT,
    )
    w.envelopes = envelopes
    return w


def _transition_envelope(bead_id: str, to_state: str, hours_ago: float) -> dict:
    return {
        "signal_type": "bead_transition",
        "service": CAT_SERVICE,
        "env": _ENV,
        "ts": _ts(hours_ago),
        "message": f"BEAD {bead_id} → {to_state}",
        "severity": "info",
        "commit_sha": _COMMIT,
        "deploy_id": _SPRINT,
        "attrs": {"entity_id": bead_id, "entity_type": "bead", "from_state": "active", "to_state": to_state, "event": "start"},
    }


def _go_envelope(allowed: bool, ts_str: str) -> dict:
    return {
        "signal_type": "go_decision",
        "service": CAT_SERVICE,
        "env": _ENV,
        "ts": ts_str,
        "message": f"GO {'allowed' if allowed else 'blocked'}",
        "severity": "error" if not allowed else "info",
        "commit_sha": _COMMIT,
        "deploy_id": _SPRINT,
        "attrs": {"allowed": allowed, "drift_count": 0 if allowed else 1, "drifts": [] if allowed else ["COLLISION"], "sprint": _SPRINT},
    }


def _closeout_envelope(allowed: bool, ts_str: str, reason: str = "") -> dict:
    return {
        "signal_type": "closeout",
        "service": CAT_SERVICE,
        "env": _ENV,
        "ts": ts_str,
        "message": f"closeout {'allowed' if allowed else 'blocked'}",
        "severity": "error" if not allowed else "info",
        "commit_sha": _COMMIT,
        "deploy_id": _SPRINT,
        "attrs": {"target_id": "BEAD-X", "target_type": "bead", "allowed": allowed, "reason": reason, "actor": "pytest", "errors": []},
    }


def _agent_envelope(confidence: float) -> dict:
    return {
        "signal_type": "agent_run",
        "service": CAT_SERVICE,
        "env": _ENV,
        "ts": _ts(),
        "message": "agent run",
        "severity": "warn" if confidence < 70 else "info",
        "commit_sha": _COMMIT,
        "deploy_id": _SPRINT,
        "attrs": {"task_id": "BEAD-TEST", "model": "test-model", "role": "worker", "confidence_score": confidence, "risk_level": "low", "tools_used": 1, "files_touched": [], "result": "test", "validation": ""},
    }


# ─── adapter unit tests ───────────────────────────────────────────────────────

class TestCatAdapter:
    def test_adapt_transition_produces_envelope(self):
        records = [{"timestamp": _ts(), "entity_id": "BEAD-X", "entity_type": "bead", "from_state": "active", "to_state": "in_progress", "event": "start"}]
        result = _adapt_transitions(records, _COMMIT, _SPRINT, _ENV)
        assert len(result) == 1
        assert result[0]["signal_type"] == "bead_transition"
        assert result[0]["service"] == CAT_SERVICE

    def test_adapt_closeout_allowed_severity_info(self):
        records = [{"timestamp": _ts(), "allowed": True, "target_id": "BEAD-X", "reason": "ok", "actor": "test", "errors": []}]
        result = _adapt_closeouts(records, _COMMIT, _SPRINT, _ENV)
        assert result[0]["severity"] == "info"

    def test_adapt_closeout_blocked_severity_error(self):
        records = [{"timestamp": _ts(), "allowed": False, "target_id": "BEAD-X", "reason": "missing artifact", "actor": "test", "errors": ["missing artifact"]}]
        result = _adapt_closeouts(records, _COMMIT, _SPRINT, _ENV)
        assert result[0]["severity"] == "error"

    def test_adapt_go_decision_blocked(self):
        records = [{"ts": _ts(), "allowed": False, "drift_count": 1, "drifts": ["COLLISION"], "sprint": _SPRINT}]
        result = _adapt_go_decisions(records, _COMMIT, _SPRINT, _ENV)
        assert result[0]["severity"] == "error"
        assert result[0]["attrs"]["allowed"] is False

    def test_adapt_agent_run_low_confidence_warn(self):
        records = [{"ts": _ts(), "task_id": "BEAD-X", "model": "m", "role": "worker", "confidence_score": 50.0, "risk_level": "low", "tools_used": 1, "files_touched": [], "result": "ok", "validation": ""}]
        result = _adapt_agent_runs(records, _COMMIT, _SPRINT, _ENV)
        assert result[0]["severity"] == "warn"

    def test_adapter_skips_schema_header(self):
        header = {"_schema": "AGENT_RUN_LOG v1", "_fields": ["task_id"]}
        run = {"ts": _ts(), "task_id": "X", "model": "m", "role": "worker", "confidence_score": 80.0, "risk_level": "low", "tools_used": 0, "files_touched": [], "result": "ok", "validation": ""}
        result = _adapt_agent_runs([header, run], _COMMIT, _SPRINT, _ENV)
        assert len(result) == 1

    def test_adapter_skips_dry_run_closeouts(self):
        records = [
            {"timestamp": _ts(), "allowed": False, "target_id": "BEAD-X", "reason": "test mismatch", "actor": "pytest", "errors": [], "dry_run": True},
            {"timestamp": _ts(), "allowed": False, "target_id": "BEAD-Y", "reason": "real rejection", "actor": "Human Owner", "errors": []},
        ]
        result = _adapt_closeouts(records, _COMMIT, _SPRINT, _ENV)
        assert len(result) == 1
        assert result[0]["attrs"]["target_id"] == "BEAD-Y"


# ─── rule: bead-stuck-in-state ────────────────────────────────────────────────

class TestBeadStuckInState:
    def test_no_finding_when_bead_recent(self):
        window = _make_window([_transition_envelope("BEAD-X", "in_progress", hours_ago=1)])
        assert rule_bead_stuck_in_state(window) == []

    def test_p2_finding_at_25h(self):
        window = _make_window([_transition_envelope("BEAD-X", "in_progress", hours_ago=25)])
        findings = rule_bead_stuck_in_state(window)
        assert len(findings) == 1
        assert findings[0]["severity"] == "p2"
        assert findings[0]["rule_id"] == "bead-stuck-in-state"

    def test_p1_finding_at_50h(self):
        window = _make_window([_transition_envelope("BEAD-X", "in_progress", hours_ago=50)])
        findings = rule_bead_stuck_in_state(window)
        assert len(findings) == 1
        assert findings[0]["severity"] == "p1"

    def test_no_finding_when_bead_completed(self):
        window = _make_window([_transition_envelope("BEAD-X", "completed", hours_ago=50)])
        assert rule_bead_stuck_in_state(window) == []

    def test_no_finding_for_non_cat_service(self):
        w = CorrelationWindow(service="other-service", env="prod", commit_sha="abc1234", deploy_id="SPRINT-001")
        w.envelopes = [_transition_envelope("BEAD-X", "in_progress", hours_ago=50)]
        assert rule_bead_stuck_in_state(w) == []

    def test_finding_has_evidence(self):
        window = _make_window([_transition_envelope("BEAD-X", "validating", hours_ago=30)])
        findings = rule_bead_stuck_in_state(window)
        assert findings and len(findings[0]["evidence"]) >= 1


# ─── rule: go-block-frequency ─────────────────────────────────────────────────

class TestGoBlockFrequency:
    def _blocked_events(self, count: int, spread_minutes: int = 10) -> list[dict]:
        base = datetime.now(timezone.utc)
        events = []
        for i in range(count):
            t = (base - timedelta(minutes=i * spread_minutes)).isoformat()
            events.append(_go_envelope(allowed=False, ts_str=t))
        return events

    def test_no_finding_with_two_blocks(self):
        window = _make_window(self._blocked_events(2))
        assert rule_go_block_frequency(window) is None

    def test_p1_finding_with_three_blocks_in_1h(self):
        window = _make_window(self._blocked_events(3, spread_minutes=10))
        finding = rule_go_block_frequency(window)
        assert finding is not None
        assert finding["severity"] == "p1"
        assert finding["rule_id"] == "go-block-frequency"

    def test_p0_finding_with_five_blocks_in_1h(self):
        window = _make_window(self._blocked_events(5, spread_minutes=10))
        finding = rule_go_block_frequency(window)
        assert finding is not None
        assert finding["severity"] == "p0"

    def test_no_finding_when_blocks_spread_beyond_1h(self):
        # 3 blocks but spread over 3h — no 1h window has >=3
        window = _make_window(self._blocked_events(3, spread_minutes=70))
        assert rule_go_block_frequency(window) is None

    def test_allowed_events_not_counted(self):
        allowed = [_go_envelope(True, _ts(i * 0.1)) for i in range(10)]
        window = _make_window(allowed)
        assert rule_go_block_frequency(window) is None

    def test_finding_has_evidence(self):
        window = _make_window(self._blocked_events(3))
        finding = rule_go_block_frequency(window)
        assert finding and len(finding["evidence"]) >= 1


# ─── rule: closeout-rejection-spike ──────────────────────────────────────────

class TestCloseoutRejectionSpike:
    def _mixed_closeouts(self, rejected: int, allowed: int, spread_minutes: int = 15) -> list[dict]:
        base = datetime.now(timezone.utc)
        events = []
        for i in range(rejected):
            t = (base - timedelta(minutes=i * spread_minutes)).isoformat()
            events.append(_closeout_envelope(False, t, reason="missing artifact"))
        for i in range(allowed):
            t = (base - timedelta(minutes=(rejected + i) * spread_minutes)).isoformat()
            events.append(_closeout_envelope(True, t))
        return events

    def test_no_finding_below_50pct(self):
        # 1 rejected, 3 allowed = 25% — no finding
        window = _make_window(self._mixed_closeouts(1, 3))
        assert rule_closeout_rejection_spike(window) is None

    def test_p2_finding_at_50pct(self):
        # 2 rejected, 2 allowed = 50%
        window = _make_window(self._mixed_closeouts(2, 2))
        finding = rule_closeout_rejection_spike(window)
        assert finding is not None
        assert finding["severity"] == "p2"

    def test_p0_finding_at_80pct(self):
        # 4 rejected, 1 allowed = 80%
        window = _make_window(self._mixed_closeouts(4, 1))
        finding = rule_closeout_rejection_spike(window)
        assert finding is not None
        assert finding["severity"] == "p0"

    def test_no_finding_with_single_closeout(self):
        window = _make_window([_closeout_envelope(False, _ts())])
        assert rule_closeout_rejection_spike(window) is None

    def test_finding_has_evidence(self):
        window = _make_window(self._mixed_closeouts(2, 2))
        finding = rule_closeout_rejection_spike(window)
        assert finding and len(finding["evidence"]) >= 1


# ─── rule: confidence-below-threshold ────────────────────────────────────────

class TestConfidenceBelowThreshold:
    def test_no_finding_above_threshold(self):
        window = _make_window([_agent_envelope(85.0)])
        assert rule_confidence_below_threshold(window) == []

    def test_p2_finding_below_threshold(self):
        window = _make_window([_agent_envelope(55.0)])
        findings = rule_confidence_below_threshold(window)
        assert len(findings) == 1
        assert findings[0]["severity"] == "p2"
        assert findings[0]["rule_id"] == "confidence-below-threshold"

    def test_finding_at_exactly_threshold_no_fire(self):
        window = _make_window([_agent_envelope(70.0)])
        assert rule_confidence_below_threshold(window) == []

    def test_multiple_low_confidence_runs(self):
        window = _make_window([_agent_envelope(50.0), _agent_envelope(60.0), _agent_envelope(85.0)])
        findings = rule_confidence_below_threshold(window)
        assert len(findings) == 2

    def test_finding_has_evidence(self):
        window = _make_window([_agent_envelope(40.0)])
        findings = rule_confidence_below_threshold(window)
        assert findings and len(findings[0]["evidence"]) >= 1


# ─── normalize accepts new signal types ──────────────────────────────────────

class TestNormalizerExtension:
    def _base_signal(self, signal_type: str, env: str = "local") -> dict:
        return {
            "signal_type": signal_type,
            "service": "cat",
            "env": env,
            "ts": "2026-06-18T01:00:00+00:00",
            "message": "test",
            "commit_sha": "a6aec4f",
            "deploy_id": "SPRINT-008",
        }

    @pytest.mark.parametrize("st", ["bead_transition", "closeout", "go_decision", "agent_run"])
    def test_governance_signal_types_accepted(self, st):
        envelopes, _, rejected = normalize_batch([self._base_signal(st)])
        assert len(rejected) == 0, f"Rejected with errors: {rejected}"
        assert len(envelopes) == 1

    @pytest.mark.parametrize("env", ["local", "ci"])
    def test_governance_envs_accepted(self, env):
        envelopes, _, rejected = normalize_batch([self._base_signal("bead_transition", env)])
        assert len(rejected) == 0

    def test_old_signal_types_still_accepted(self):
        signals = [self._base_signal(st, "dev") for st in ["log", "metric", "trace", "event"]]
        envelopes, _, rejected = normalize_batch(signals)
        assert len(rejected) == 0
        assert len(envelopes) == 4


# ─── end-to-end: clean fixture produces no critical findings ──────────────────

class TestSelfMonitorEndToEnd:
    def test_clean_signals_produce_no_critical_findings(self):
        fixture = Path(__file__).parent / "fixtures" / "loghouse" / "cat_self_signals.json"
        raw = json.loads(fixture.read_text())
        envelopes, deploy_events, rejected = normalize_batch(raw)
        assert len(rejected) == 0, f"Unexpected rejections: {rejected}"
        windows = correlate(envelopes, deploy_events)
        findings = evaluate_windows(windows)
        critical = [f for f in findings if f.get("severity") in {"p0", "p1"}]
        assert critical == [], f"Unexpected critical findings: {critical}"
