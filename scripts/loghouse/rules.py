"""
LOGHOUSE Rules Engine.

Implements deterministic rules in two groups:

Service telemetry rules (external signal types):
1. error-spike-after-deploy  — error count spikes within a deploy window
2. forbidden-dependency-edge — observed edge is forbidden by architecture rules
3. exception-explosion       — high count of exception events in a window

CAT governance rules (self-observability, signal_type in bead_transition/closeout/
go_decision/agent_run; only fire on windows where service="cat"):
4. bead-stuck-in-state       — BEAD stalled in in_progress/validating >24h
5. go-block-frequency        — GO blocked >=3 times within any 1h window
6. closeout-rejection-spike  — >=50% of closeouts rejected in any 2h window
7. confidence-below-threshold — agent_run confidence_score < 70

Evidence-first: a finding with no evidence is NEVER emitted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.loghouse.correlate import CorrelationWindow

ERROR_SPIKE_THRESHOLD = 3  # minimum errors to trigger
EXCEPTION_EXPLOSION_THRESHOLD = 3  # minimum exceptions to trigger


def rule_error_spike_after_deploy(window: CorrelationWindow) -> dict[str, Any] | None:
    """
    Emit a finding if a deploy event is followed by a spike in error-severity logs.
    Requires: deploy_event present AND error_count >= ERROR_SPIKE_THRESHOLD.
    """
    if not window.has_deploy_event():
        return None

    error_events = [e for e in window.envelopes if e.get("severity") in ("error", "fatal")]
    if len(error_events) < ERROR_SPIKE_THRESHOLD:
        return None

    deploy_event = window.deploy_events[0]
    first_error = error_events[0]

    evidence = [
        {
            "source_type": "deploy",
            "source_ref": deploy_event["deploy_id"],
            "observed_at": deploy_event["completed_at"],
            "summary": (
                f"Deploy {deploy_event['deploy_id']} completed at {deploy_event['completed_at']}; "
                f"{len(error_events)} error(s) observed in {window.service} within the correlation window."
            ),
        },
        {
            "source_type": "log",
            "source_ref": first_error.get("event_id", "unknown"),
            "observed_at": first_error["ts"],
            "summary": f"First error after deploy: {first_error.get('message', '')[:120]}",
        },
    ]

    return {
        "rule_id": "error-spike-after-deploy",
        "title": f"Error spike after deploy in {window.service}",
        "category": "reliability",
        "severity": "p1",
        "confidence": min(0.5 + 0.1 * len(error_events), 0.95),
        "services": [window.service],
        "first_seen": first_error["ts"],
        "last_seen": error_events[-1]["ts"],
        "owner": f"team-{window.service.split('-')[0]}",
        "hypothesis": (
            f"The deploy {deploy_event['deploy_id']} introduced a regression causing "
            f"{len(error_events)} errors in {window.service}."
        ),
        "suggested_fix": (
            f"Review changes in commit {window.commit_sha} and consider rollback of "
            f"{deploy_event['deploy_id']} if error rate does not recover."
        ),
        "blast_radius": "service",
        "sla_impact": True,
        "evidence": evidence,
    }


def rule_forbidden_dependency_edge(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Emit a finding for each dependency_edge record that is explicitly not allowed.
    Evidence: the edge record itself.
    """
    findings = []
    for edge in edges:
        if edge.get("allowed") is False:
            evidence = [
                {
                    "source_type": "dependency",
                    "source_ref": edge.get("edge_id", "unknown"),
                    "observed_at": edge.get("observed_at", "1970-01-01T00:00:00Z"),
                    "summary": (
                        f"Forbidden dependency edge observed: {edge.get('source')} → {edge.get('target')} "
                        f"(type: {edge.get('edge_type')}). "
                        f"rule_id: {edge.get('rule_id', 'none')}. confidence: {edge.get('confidence', 0)}"
                    ),
                }
            ]
            findings.append(
                {
                    "rule_id": "forbidden-dependency-edge",
                    "title": f"Forbidden dependency: {edge.get('source')} → {edge.get('target')}",
                    "category": "drift",
                    "severity": "p1",
                    "confidence": float(edge.get("confidence", 0.8)),
                    "services": [edge.get("source", "unknown"), edge.get("target", "unknown")],
                    "first_seen": edge.get("observed_at", "1970-01-01T00:00:00Z"),
                    "last_seen": edge.get("observed_at", "1970-01-01T00:00:00Z"),
                    "owner": f"team-{edge.get('source', 'unknown').split('-')[0]}",
                    "hypothesis": (
                        f"Service {edge.get('source')} is calling {edge.get('target')} "
                        "which is declared forbidden by architecture rules."
                    ),
                    "suggested_fix": (
                        f"Remove the dependency from {edge.get('source')} to {edge.get('target')} "
                        "and route through the approved pathway."
                    ),
                    "blast_radius": "domain",
                    "sla_impact": False,
                    "evidence": evidence,
                }
            )
    return findings


def rule_exception_explosion(window: CorrelationWindow) -> dict[str, Any] | None:
    """
    Emit a finding if exception count in a window exceeds the threshold.
    """
    exception_events = [
        e for e in window.envelopes
        if e.get("severity") in ("error", "fatal")
        or "exception" in e.get("message", "").lower()
        or "traceback" in e.get("message", "").lower()
    ]

    if len(exception_events) < EXCEPTION_EXPLOSION_THRESHOLD:
        return None

    sample_refs = [e.get("event_id", "unknown") for e in exception_events[:3]]
    evidence = [
        {
            "source_type": "log",
            "source_ref": ref,
            "observed_at": exception_events[i]["ts"],
            "summary": f"Exception event: {exception_events[i].get('message', '')[:80]}",
        }
        for i, ref in enumerate(sample_refs)
    ]

    return {
        "rule_id": "exception-explosion",
        "title": f"Exception explosion in {window.service}",
        "category": "reliability",
        "severity": "p2",
        "confidence": min(0.4 + 0.1 * len(exception_events), 0.90),
        "services": [window.service],
        "first_seen": exception_events[0]["ts"],
        "last_seen": exception_events[-1]["ts"],
        "owner": f"team-{window.service.split('-')[0]}",
        "hypothesis": (
            f"{len(exception_events)} exception/error events detected in {window.service} "
            "within a single correlation window, suggesting a widespread failure."
        ),
        "suggested_fix": (
            f"Inspect the exception traces in {window.service}, check for recent config changes, "
            "and review dependency health."
        ),
        "blast_radius": "service",
        "sla_impact": True,
        "evidence": evidence,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CAT Governance Rules (self-observability)
# Only fire on CorrelationWindows where service == "cat".
# ─────────────────────────────────────────────────────────────────────────────

CAT_SERVICE = "cat"

BEAD_STUCK_WARN_HOURS = 24   # P2 threshold
BEAD_STUCK_CRIT_HOURS = 48   # P1 threshold
GO_BLOCK_P1_THRESHOLD = 3    # blocks in 1h → P1
GO_BLOCK_P0_THRESHOLD = 5    # blocks in 1h → P0
CLOSEOUT_SPIKE_P2_PCT = 0.50  # ≥50% rejected in 2h → P2
CLOSEOUT_SPIKE_P0_PCT = 0.80  # ≥80% rejected in 2h → P0
CONFIDENCE_MINIMUM = 70.0


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _max_in_window(
    events: list[dict[str, Any]], window_hours: float
) -> list[dict[str, Any]]:
    """Return the largest subset of events that fit within window_hours."""
    if not events:
        return []
    sorted_evs = sorted(events, key=lambda e: e.get("ts", ""))
    best: list[dict[str, Any]] = []
    for i, ev in enumerate(sorted_evs):
        anchor = _parse_ts(ev.get("ts", ""))
        if anchor is None:
            continue
        cutoff = anchor + timedelta(hours=window_hours)
        group = [
            e for e in sorted_evs[i:]
            if (_parse_ts(e.get("ts", "")) or datetime.min.replace(tzinfo=timezone.utc)) <= cutoff
        ]
        if len(group) > len(best):
            best = group
    return best


def rule_bead_stuck_in_state(window: CorrelationWindow) -> list[dict[str, Any]]:
    """
    Emit a finding for each BEAD that has been in in_progress or validating
    for more than BEAD_STUCK_WARN_HOURS without a subsequent transition.
    P2 at 24h, P1 at 48h.
    """
    if window.service != CAT_SERVICE:
        return []

    transitions = [e for e in window.envelopes if e.get("signal_type") == "bead_transition"]
    if not transitions:
        return []

    # Build per-BEAD last-seen state
    bead_latest: dict[str, dict[str, Any]] = {}
    for ev in transitions:
        attrs = ev.get("attrs", {})
        bead_id = attrs.get("entity_id", "")
        ts_str = ev.get("ts", "")
        if not bead_id:
            continue
        prev = bead_latest.get(bead_id)
        if prev is None or ts_str > prev["ts"]:
            bead_latest[bead_id] = {"ts": ts_str, "state": attrs.get("to_state", ""), "envelope": ev}

    stuck_states = {"in_progress", "validating"}
    now = datetime.now(timezone.utc)
    findings = []

    for bead_id, info in bead_latest.items():
        if info["state"] not in stuck_states:
            continue
        last_ts = _parse_ts(info["ts"])
        if last_ts is None:
            continue
        elapsed_h = (now - last_ts).total_seconds() / 3600
        if elapsed_h < BEAD_STUCK_WARN_HOURS:
            continue

        severity = "p1" if elapsed_h >= BEAD_STUCK_CRIT_HOURS else "p2"
        elapsed_str = f"{elapsed_h:.1f}h"
        ev = info["envelope"]

        evidence = [{
            "source_type": "transition_log",
            "source_ref": f"evidence/transitions/transition_log.jsonl",
            "observed_at": info["ts"],
            "summary": (
                f"BEAD {bead_id} entered state '{info['state']}' {elapsed_str} ago "
                "with no subsequent transition recorded."
            ),
        }]

        findings.append({
            "rule_id": "bead-stuck-in-state",
            "title": f"BEAD {bead_id} stuck in '{info['state']}' for {elapsed_str}",
            "category": "governance",
            "severity": severity,
            "confidence": 0.95,
            "services": [CAT_SERVICE],
            "first_seen": info["ts"],
            "last_seen": info["ts"],
            "owner": "Human Owner",
            "hypothesis": (
                f"BEAD {bead_id} has been in '{info['state']}' for {elapsed_str} without "
                "a transition. The work may be blocked, abandoned, or the state engine "
                "failed to record a subsequent transition."
            ),
            "suggested_fix": (
                f"Run `python scripts/cat_transition.py` to advance {bead_id}, or "
                "investigate whether the BEAD was completed without a recorded closeout."
            ),
            "blast_radius": "bead",
            "sla_impact": False,
            "evidence": evidence,
        })

    return findings


def rule_go_block_frequency(window: CorrelationWindow) -> dict[str, Any] | None:
    """
    Emit a finding if GO is blocked >=3 times within any 1-hour window.
    P1 at 3–4 blocks, P0 at >=5.
    """
    if window.service != CAT_SERVICE:
        return None

    go_events = [e for e in window.envelopes if e.get("signal_type") == "go_decision"]
    blocked = [e for e in go_events if not e.get("attrs", {}).get("allowed", True)]

    if len(blocked) < GO_BLOCK_P1_THRESHOLD:
        return None

    densest = _max_in_window(blocked, window_hours=1.0)
    if len(densest) < GO_BLOCK_P1_THRESHOLD:
        return None

    count = len(densest)
    severity = "p0" if count >= GO_BLOCK_P0_THRESHOLD else "p1"
    first_ev = densest[0]
    last_ev = densest[-1]

    all_drifts: list[str] = []
    for ev in densest:
        all_drifts.extend(ev.get("attrs", {}).get("drifts", []))
    drift_summary = ", ".join(sorted(set(all_drifts))) or "unknown"

    evidence = [{
        "source_type": "go_decisions",
        "source_ref": "evidence/logs/go_decisions.jsonl",
        "observed_at": first_ev.get("ts", ""),
        "summary": (
            f"{count} GO blocks detected within 1 hour "
            f"(first: {first_ev.get('ts', '')} → last: {last_ev.get('ts', '')}). "
            f"Drift causes: {drift_summary}."
        ),
    }]

    return {
        "rule_id": "go-block-frequency",
        "title": f"GO blocked {count}× in 1h — governance health degraded",
        "category": "governance",
        "severity": severity,
        "confidence": 0.99,
        "services": [CAT_SERVICE],
        "first_seen": first_ev.get("ts", ""),
        "last_seen": last_ev.get("ts", ""),
        "owner": "Human Owner",
        "hypothesis": (
            f"GO was blocked {count} times within a 1-hour window, suggesting a "
            "systemic governance misalignment rather than an isolated incident. "
            f"Recurring drift causes: {drift_summary}."
        ),
        "suggested_fix": (
            "Run `python scripts/cat_align_check.py --strict` and resolve all reported "
            "drifts before re-running GO. If drifts recur after each fix, review "
            "the mission lifecycle scripts for a root-cause loop."
        ),
        "blast_radius": "sprint",
        "sla_impact": False,
        "evidence": evidence,
    }


def rule_closeout_rejection_spike(window: CorrelationWindow) -> dict[str, Any] | None:
    """
    Emit a finding if >=50% of closeouts in any 2-hour window were rejected.
    P2 at 50–79%, P0 at >=80%.
    """
    if window.service != CAT_SERVICE:
        return None

    closeouts = [e for e in window.envelopes if e.get("signal_type") == "closeout"]
    if len(closeouts) < 2:
        return None

    densest_all = _max_in_window(closeouts, window_hours=2.0)
    if len(densest_all) < 2:
        return None

    rejected = [e for e in densest_all if e.get("attrs", {}).get("allowed") is False]
    pct = len(rejected) / len(densest_all)

    if pct < CLOSEOUT_SPIKE_P2_PCT:
        return None

    severity = "p0" if pct >= CLOSEOUT_SPIKE_P0_PCT else "p2"
    reasons = [e.get("attrs", {}).get("reason", "") for e in rejected if e.get("attrs", {}).get("reason")]
    reason_summary = "; ".join(sorted(set(r for r in reasons if r))) or "see closeout log"
    first_ev = densest_all[0]
    last_ev = densest_all[-1]

    evidence = [{
        "source_type": "closeouts",
        "source_ref": "evidence/logs/closeouts.jsonl",
        "observed_at": first_ev.get("ts", ""),
        "summary": (
            f"{len(rejected)} of {len(densest_all)} closeout attempts rejected in 2h "
            f"({pct * 100:.0f}%). Rejection reasons: {reason_summary}."
        ),
    }]

    return {
        "rule_id": "closeout-rejection-spike",
        "title": f"Evidence gate rejecting {pct * 100:.0f}% of closeouts in 2h window",
        "category": "governance",
        "severity": severity,
        "confidence": 0.95,
        "services": [CAT_SERVICE],
        "first_seen": first_ev.get("ts", ""),
        "last_seen": last_ev.get("ts", ""),
        "owner": "Human Owner",
        "hypothesis": (
            f"{pct * 100:.0f}% of recent closeout submissions were rejected by the evidence "
            "gate, suggesting that evidence quality or bundle structure is systematically "
            "incorrect. Reasons observed: " + reason_summary
        ),
        "suggested_fix": (
            "Review the evidence bundle format against `schemas/` definitions. "
            "Check `evidence/logs/closeouts.jsonl` for specific rejection messages. "
            "Consult `docs/runbooks/loghouse-incident-to-finding.md` for evidence quality guidance."
        ),
        "blast_radius": "sprint",
        "sla_impact": False,
        "evidence": evidence,
    }


def rule_confidence_below_threshold(window: CorrelationWindow) -> list[dict[str, Any]]:
    """
    Emit a P2 finding for each agent_run envelope with confidence_score < 70.
    """
    if window.service != CAT_SERVICE:
        return []

    agent_runs = [e for e in window.envelopes if e.get("signal_type") == "agent_run"]
    findings = []

    for ev in agent_runs:
        score = float(ev.get("attrs", {}).get("confidence_score", 100))
        if score >= CONFIDENCE_MINIMUM:
            continue

        task_id = ev.get("attrs", {}).get("task_id", "unknown")
        model = ev.get("attrs", {}).get("model", "unknown")
        result_text = ev.get("attrs", {}).get("result", "")

        evidence = [{
            "source_type": "agent_run_log",
            "source_ref": "evidence/logs/AGENT_RUN_LOG.jsonl",
            "observed_at": ev.get("ts", ""),
            "summary": (
                f"Agent run for {task_id} reported confidence {score:.0f} "
                f"(minimum: {CONFIDENCE_MINIMUM:.0f}). Model: {model}. Result: {result_text[:80]}"
            ),
        }]

        findings.append({
            "rule_id": "confidence-below-threshold",
            "title": f"Agent run [{task_id}] confidence {score:.0f} below minimum {CONFIDENCE_MINIMUM:.0f}",
            "category": "governance",
            "severity": "p2",
            "confidence": 0.99,
            "services": [CAT_SERVICE],
            "first_seen": ev.get("ts", ""),
            "last_seen": ev.get("ts", ""),
            "owner": "Human Owner",
            "hypothesis": (
                f"The agent that worked on {task_id} reported a confidence score of {score:.0f}, "
                f"below CAT's configured minimum of {CONFIDENCE_MINIMUM:.0f}. "
                "The output may require additional review before acceptance."
            ),
            "suggested_fix": (
                f"Review the output of agent run [{task_id}] before closing the BEAD. "
                "Consider re-running or supplementing with a higher-confidence review pass."
            ),
            "blast_radius": "bead",
            "sla_impact": False,
            "evidence": evidence,
        })

    return findings


def evaluate_windows(
    windows: list[CorrelationWindow],
    dependency_edges: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Run all rules against correlation windows and dependency edges.
    Returns a list of raw finding dicts (not yet schema-validated).
    """
    raw_findings: list[dict[str, Any]] = []

    for window in windows:
        # Service telemetry rules (skip CAT governance windows)
        if window.service != CAT_SERVICE:
            finding = rule_error_spike_after_deploy(window)
            if finding:
                raw_findings.append(finding)

            finding = rule_exception_explosion(window)
            if finding:
                raw_findings.append(finding)
        else:
            # CAT governance rules
            raw_findings.extend(rule_bead_stuck_in_state(window))

            finding = rule_go_block_frequency(window)
            if finding:
                raw_findings.append(finding)

            finding = rule_closeout_rejection_spike(window)
            if finding:
                raw_findings.append(finding)

            raw_findings.extend(rule_confidence_below_threshold(window))

    if dependency_edges:
        raw_findings.extend(rule_forbidden_dependency_edge(dependency_edges))

    return raw_findings
