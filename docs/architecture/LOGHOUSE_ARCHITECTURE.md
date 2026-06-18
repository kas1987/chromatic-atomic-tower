# LOGHOUSE Architecture

## Overview

LOGHOUSE is a local-first, evidence-first log intelligence and architecture drift MVP inside Chromatic Atomic Tower. It consumes heterogeneous telemetry, normalizes it into canonical envelopes, correlates signals across time windows, and emits audit-ready findings with evidence.

## Components

### Intake Layer
- **OTel Collector** (`reference/loghouse/otel-collector.yaml`): receives logs, metrics, and traces from services; enriches required attributes; exports to file.
- **Vector Pipeline** (`reference/loghouse/vector.yaml`): tails log files, transforms fields to match `telemetry_envelope`, forwards to local sink.

### Normalizer (`scripts/loghouse/normalize.py`)
- **Inputs**: raw signal dicts (logs, metrics, traces, deploy events)
- **Outputs**: `telemetry_envelope`-valid records and `deploy_event`-valid records
- **Rejects**: records missing required attributes (`service`, `env`, `signal_type`, `ts`, `commit_sha`, `deploy_id`)

### Correlator (`scripts/loghouse/correlate.py`)
- **Inputs**: normalized telemetry envelopes and deploy events
- **Outputs**: correlation windows keyed by `(service, env, commit_sha, deploy_id, trace_id)`
- **Purpose**: groups signals that belong to the same deployment context for rule evaluation

### Rules Engine (`scripts/loghouse/rules.py`)
- **Inputs**: correlation windows
- **Outputs**: raw finding dicts with evidence items
- **Rules**:
  - `error-spike-after-deploy`: detects error-rate spike within a window after a deploy event
  - `forbidden-dependency-edge`: detects dependency edges classified as blocked/forbidden
  - `exception-explosion`: detects a high count of exception-severity events in a window

### Findings Engine (`scripts/loghouse/findings.py`)
- **Inputs**: raw finding dicts from rules
- **Outputs**: `finding.schema.json`-valid JSON records and a Markdown report
- **Constraint**: every finding must have at least one evidence item

### Dispatch Writer (`scripts/loghouse/dispatch.py`)
- **Inputs**: validated findings
- **Outputs**: `dispatch_queue_item.schema.json`-valid records with owner, evidence reference, acceptance criteria, and stop condition

### Drift Detector (`scripts/loghouse/drift.py`)
- **Inputs**: observed `dependency_edge` records + `architecture_rules.yaml`
- **Outputs**: `drift_report.schema.json`-valid report; forbidden edges produce findings via the findings engine
- **Classifications**: `intentional` | `accidental` | `blocked` | `unknown`

### CLI (`scripts/cat_loghouse.py`)
- Orchestrates: normalize → correlate → rules → findings → dispatch over an input fixture directory

## Evidence-First Principle

No finding may be emitted without at least one attached evidence item that references a real signal. Evidence items carry `source_type`, `source_ref`, `observed_at`, and a human-readable `summary`. This ensures findings are auditable and not model-generated speculation.

## Data Contracts

| Schema | Purpose |
|---|---|
| `telemetry_envelope.schema.json` | Canonical signal record |
| `deploy_event.schema.json` | Deployment lifecycle event |
| `dependency_edge.schema.json` | Observed service dependency |
| `finding.schema.json` | Evidence-backed anomaly finding |
| `dispatch_queue_item.schema.json` | Agent-routable remediation task |
| `architecture_rule.schema.json` | Allowed/forbidden dependency declaration |
| `drift_report.schema.json` | Drift classification report |
