"""
LOGHOUSE Correlator.

Groups normalized telemetry_envelope records and deploy_events into
CorrelationWindow objects keyed by (service, env, commit_sha, deploy_id, trace_id).

The findings engine receives these windows.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationWindow:
    """A group of signals sharing the same deployment context."""

    service: str
    env: str
    commit_sha: str
    deploy_id: str
    trace_id: str = ""

    envelopes: list[dict[str, Any]] = field(default_factory=list)
    deploy_events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        return (self.service, self.env, self.commit_sha, self.deploy_id, self.trace_id)

    def error_count(self) -> int:
        return sum(1 for e in self.envelopes if e.get("severity") in ("error", "fatal"))

    def exception_count(self) -> int:
        return sum(
            1
            for e in self.envelopes
            if e.get("severity") in ("error", "fatal")
            or "exception" in e.get("message", "").lower()
            or "traceback" in e.get("message", "").lower()
        )

    def has_deploy_event(self) -> bool:
        return len(self.deploy_events) > 0

    def total_events(self) -> int:
        return len(self.envelopes)


def correlate(
    envelopes: list[dict[str, Any]],
    deploy_events: list[dict[str, Any]],
) -> list[CorrelationWindow]:
    """
    Group normalized records into CorrelationWindow objects.

    Key: (service, env, commit_sha, deploy_id, trace_id).
    Deploy events with matching (service, commit_sha, deploy_id) are
    attached to all windows for that deployment context.
    """
    window_map: dict[tuple, CorrelationWindow] = {}

    for envelope in envelopes:
        service = envelope.get("service", "")
        env = envelope.get("env", "")
        commit_sha = envelope.get("commit_sha", "")
        deploy_id = envelope.get("deploy_id", "")
        trace_id = envelope.get("trace_id", "")

        key = (service, env, commit_sha, deploy_id, trace_id)
        if key not in window_map:
            window_map[key] = CorrelationWindow(
                service=service,
                env=env,
                commit_sha=commit_sha,
                deploy_id=deploy_id,
                trace_id=trace_id,
            )
        window_map[key].envelopes.append(envelope)

    # Attach deploy events to matching windows
    for deploy_event in deploy_events:
        d_service = deploy_event.get("service", "")
        d_commit = deploy_event.get("commit_sha", "")
        d_deploy_id = deploy_event.get("deploy_id", "")

        for key, window in window_map.items():
            if (
                window.service == d_service
                and window.commit_sha == d_commit
                and window.deploy_id == d_deploy_id
            ):
                window.deploy_events.append(deploy_event)

    # If deploy events have no matching envelope windows, create a window for them
    for deploy_event in deploy_events:
        d_service = deploy_event.get("service", "")
        d_env = "prod"  # deploy events default to prod context
        d_commit = deploy_event.get("commit_sha", "")
        d_deploy_id = deploy_event.get("deploy_id", "")

        found = any(
            w.service == d_service and w.commit_sha == d_commit and w.deploy_id == d_deploy_id
            for w in window_map.values()
        )
        if not found:
            key = (d_service, d_env, d_commit, d_deploy_id, "")
            if key not in window_map:
                window_map[key] = CorrelationWindow(
                    service=d_service,
                    env=d_env,
                    commit_sha=d_commit,
                    deploy_id=d_deploy_id,
                )
                window_map[key].deploy_events.append(deploy_event)

    return list(window_map.values())
