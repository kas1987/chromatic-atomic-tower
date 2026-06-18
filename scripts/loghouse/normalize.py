"""
LOGHOUSE Normalizer.

Maps heterogeneous raw signal dicts to:
- telemetry_envelope-valid records (logs, metrics, traces)
- deploy_event-valid records

Rejects records missing required attributes.
"""

from __future__ import annotations

import uuid
from typing import Any

from scripts.common import ROOT, validate_with_schema

# Required attributes for a telemetry envelope record
ENVELOPE_REQUIRED = {"service", "env", "signal_type", "ts", "commit_sha", "deploy_id"}

# Required attributes for a deploy event record
DEPLOY_REQUIRED = {"deploy_id", "service", "commit_sha", "actor", "started_at", "completed_at", "status"}

VALID_SIGNAL_TYPES = {"log", "metric", "trace", "event"}
VALID_ENVS = {"dev", "staging", "prod"}
VALID_SEVERITIES = {"debug", "info", "warn", "error", "fatal", "na"}
VALID_DEPLOY_STATUSES = {"started", "succeeded", "failed", "rolled_back"}

ENVELOPE_SCHEMA = ROOT / "schemas" / "telemetry_envelope.schema.json"
DEPLOY_SCHEMA = ROOT / "schemas" / "deploy_event.schema.json"


def normalize_envelope(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Normalize a raw signal dict to a telemetry_envelope-valid record.

    Returns (record, errors). If errors is non-empty, record is None and the
    signal was rejected.
    """
    missing = ENVELOPE_REQUIRED - set(raw.keys())
    if missing:
        return None, [f"missing required attributes: {sorted(missing)}"]

    signal_type = raw.get("signal_type", "")
    if signal_type not in VALID_SIGNAL_TYPES:
        return None, [f"invalid signal_type '{signal_type}'; must be one of {sorted(VALID_SIGNAL_TYPES)}"]

    env = raw.get("env", "")
    if env not in VALID_ENVS:
        return None, [f"invalid env '{env}'; must be one of {sorted(VALID_ENVS)}"]

    severity = raw.get("severity", "info")
    if severity not in VALID_SEVERITIES:
        severity = "info"

    record: dict[str, Any] = {
        "event_id": raw.get("event_id") or str(uuid.uuid4()),
        "ts": raw["ts"],
        "signal_type": signal_type,
        "service": raw["service"],
        "env": env,
        "severity": severity,
        "message": raw.get("message", ""),
        "commit_sha": raw["commit_sha"],
        "deploy_id": raw["deploy_id"],
        "attrs": raw.get("attrs", {}),
    }

    # Optional fields — pass through if present
    for opt_field in ("trace_id", "span_id", "host", "region", "team", "runtime", "request_id", "user_impact_score"):
        if opt_field in raw:
            record[opt_field] = raw[opt_field]

    errors = validate_with_schema(record, ENVELOPE_SCHEMA)
    if errors:
        return None, errors
    return record, []


def normalize_deploy_event(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """
    Normalize a raw deploy event dict to a deploy_event-valid record.

    Returns (record, errors).
    """
    missing = DEPLOY_REQUIRED - set(raw.keys())
    if missing:
        return None, [f"missing required attributes: {sorted(missing)}"]

    status = raw.get("status", "")
    if status not in VALID_DEPLOY_STATUSES:
        return None, [f"invalid status '{status}'; must be one of {sorted(VALID_DEPLOY_STATUSES)}"]

    record: dict[str, Any] = {
        "deploy_id": raw["deploy_id"],
        "service": raw["service"],
        "commit_sha": raw["commit_sha"],
        "actor": raw["actor"],
        "started_at": raw["started_at"],
        "completed_at": raw["completed_at"],
        "status": status,
    }

    errors = validate_with_schema(record, DEPLOY_SCHEMA)
    if errors:
        return None, errors
    return record, []


def normalize_batch(
    raws: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Normalize a mixed batch of raw signals.

    Detects signal kind by presence of `started_at`/`completed_at` (deploy event)
    vs everything else (telemetry envelope).

    Returns (envelopes, deploy_events, rejected) where rejected contains
    {"raw": ..., "errors": [...]} dicts.
    """
    envelopes: list[dict[str, Any]] = []
    deploy_events: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in raws:
        if "started_at" in raw and "completed_at" in raw and "status" in raw and "actor" in raw:
            record, errors = normalize_deploy_event(raw)
            if errors:
                rejected.append({"raw": raw, "errors": errors})
            else:
                deploy_events.append(record)
        else:
            record, errors = normalize_envelope(raw)
            if errors:
                rejected.append({"raw": raw, "errors": errors})
            else:
                envelopes.append(record)

    return envelopes, deploy_events, rejected
