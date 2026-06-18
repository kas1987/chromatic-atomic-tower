"""
LOGHOUSE Rules Engine.

Implements three deterministic rules:
1. error-spike-after-deploy  — error count spikes within a deploy window
2. forbidden-dependency-edge — observed edge is forbidden by architecture rules
3. exception-explosion       — high count of exception events in a window

Each rule produces a raw finding dict with at least one evidence item.
Evidence-first: a finding with no evidence is NEVER emitted.
"""

from __future__ import annotations

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
        finding = rule_error_spike_after_deploy(window)
        if finding:
            raw_findings.append(finding)

        finding = rule_exception_explosion(window)
        if finding:
            raw_findings.append(finding)

    if dependency_edges:
        raw_findings.extend(rule_forbidden_dependency_edge(dependency_edges))

    return raw_findings
