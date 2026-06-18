# LOGHOUSE Data Flow

## Pipeline Overview

```
Raw Signals
    │
    ▼
[Intake Layer]
 OTel Collector / Vector
 Enriches: service, env, signal_type, ts, commit_sha, deploy_id
    │
    ▼
[Normalizer]  scripts/loghouse/normalize.py
 Maps raw dicts → telemetry_envelope-valid records
 Maps deploy payloads → deploy_event-valid records
 Rejects missing-required-attr records
    │
    ▼
[Correlator]  scripts/loghouse/correlate.py
 Groups by: service + env + commit_sha + deploy_id + trace_id
 Produces: CorrelationWindow objects
    │
    ▼
[Rules Engine]  scripts/loghouse/rules.py
 Rule: error-spike-after-deploy
   Input: CorrelationWindow with deploy_event + error-severity logs
   Evidence: deploy_id + error count
 Rule: forbidden-dependency-edge
   Input: dependency_edge records marked allowed=false
   Evidence: edge_id + rule_id
 Rule: exception-explosion
   Input: CorrelationWindow with high exception count
   Evidence: sample event_ids
    │
    ▼
[Findings Engine]  scripts/loghouse/findings.py
 Validates each raw finding against finding.schema.json
 Writes findings.json + findings.md report
    │
    ▼
[Dispatch Writer]  scripts/loghouse/dispatch.py
 Converts each finding → dispatch_queue_item
 Sets: owner, agent_role, evidence_ref, acceptance_criteria, stop_condition
    │
    ▼
Output: findings.json, findings.md, dispatch_queue.json

Parallel track:
[Dependency Graph] observed dependency_edge records
    │
    ▼
[Drift Detector]  scripts/loghouse/drift.py
 Loads architecture_rules.yaml
 Classifies each edge: intentional | accidental | blocked | unknown
 Emits drift_report.json
 Blocked edges → findings via Findings Engine
```

## Required Attribute Enrichment

Every signal entering LOGHOUSE must carry these six attributes. Intake configs inject them if missing at source:

| Attribute | Source |
|---|---|
| `service` | OTel resource attribute `service.name` |
| `env` | OTel resource attribute `deployment.environment` |
| `signal_type` | Signal kind: log / metric / trace / event |
| `ts` | Event timestamp (ISO 8601) |
| `commit_sha` | Git SHA from build metadata |
| `deploy_id` | Deployment identifier from CI |

## Evidence Chain

```
Signal observed → normalized → correlated → rule fires → evidence attached → finding emitted → dispatch created
```

Every arrow is traceable. The drift detector follows the same chain: edge observed → rule matched → classified → (if blocked) finding emitted with edge evidence.
