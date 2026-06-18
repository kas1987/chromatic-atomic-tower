# PDR-CAT-GO-AUTOMATION

## Executive Summary

The `chromatic-atomic-tower` repository is structurally strong but needs formal dispatch
packet validation, an evidence manifest index, cost guardrails, and agent scorecard mutation
to be a complete safe GO automation control loop.

Target readiness after MP-CAT-GO-AUTO-001:
- Foundation completeness: 90%+
- GO automation completeness: 80-85%
- Hands-off autonomy readiness: still gated; human-approved until incident rate is measured

## Current State

Capabilities that exist:
- Mission-first and BEAD-first governance.
- Deterministic GO resolver (`cat_resolve_go.py`).
- State transition engine (`cat_transition.py`).
- Closeout engine (`cat_closeout.py`).
- Evidence generation (`cat_evidence.py`, `cat_generate_evidence_bundle.py`).
- GitHub Actions CI (`validate-cat.yml`) with permissions, concurrency, and timeout.
- Agent scorecard base (`cat_agent_scorecard.py`).

Gaps addressed by this mission:
- Formal `go_dispatch_packet.schema.json` — GO output not yet schema-validated.
- `evidence/manifest.yaml` + `cat_evidence_index.py` — no queryable evidence index.
- `cat_cost_guard.py` — cost guardrail script not yet present.
- `cat_pr_guard.py` — PR body validation script not yet present.
- `cat_score_agent.py` — scorecard mutation script not yet present.
- Tests for each of the above.

## System Goals

1. Make GO deterministic and schema-validated.
2. Make closeout evidence-bound.
3. Make state mutation script-controlled.
4. Make GitHub workflow cost-safe (cost guard enforces this).
5. Make agent behavior measurable (scorecard mutation).
6. Make unsafe automation fail closed.

## Non-Goals

- No uncontrolled cloud agent execution.
- No hidden billing-generating workflows.
- No writes outside declared BEAD scope.
- No secrets committed to repo.

## Proposed Architecture

```text
GO command
  -> cat_resolve_go.py --format json --check-schema
  -> go_dispatch_packet.json (validates against schema)
  -> agent/human executes BEAD
  -> validation commands run
  -> evidence artifacts written
  -> cat_evidence_index.py indexes evidence into manifest.yaml
  -> cat_closeout.py verifies evidence and validation
  -> cat_transition.py mutates BEAD/mission state
  -> cat_score_agent.py updates agent scorecard
```

## Control Points

| Control | Purpose | Fail Behavior |
|---|---|---|
| Mission registry | Prevent orphan work | Block dispatch |
| BEAD allowed paths | Prevent scope creep | Block mutation |
| State transition rules | Prevent invalid lifecycle changes | Nonzero exit |
| Evidence manifest | Prevent unverifiable closeout | Block closeout |
| Cost guard | Prevent runner/API spend surprises | Fail CI |
| PR guard | Prevent untraceable merges | Fail PR validation |
| Agent scorecard | Track trust and incidents | Reduce routing priority |

## Implementation Plan

### BEAD-CAT-GO-001: State Transition Engine
Validate and harden `cat_transition.py`, add transition schema and tests.

### BEAD-CAT-GO-002: Closeout + Evidence Schema
Validate `cat_closeout.py`, add `evidence_manifest.schema.json`, seed `evidence/manifest.yaml`, tests.

### BEAD-CAT-GO-003: Evidence Index
Build `cat_evidence_index.py`, rebuild manifest from evidence folder, tests.

### BEAD-CAT-GO-004: GitHub Actions Cost Guard
Implement `cat_cost_guard.py`, verify `validate-cat.yml` hardening, tests.

### BEAD-CAT-GO-005: GitHub PR Bridge
Add PR/issue templates, implement `cat_pr_guard.py`, tests.

### BEAD-CAT-GO-006: Agent Scorecard Mutation
Implement `cat_score_agent.py`, ensure `agents/scorecards/` directory, tests.

### BEAD-CAT-GO-007: GO Dispatch Packet Standard
Upgrade `cat_resolve_go.py` output to validate against `go_dispatch_packet.schema.json`, tests.

## Acceptance Criteria

1. `python scripts/cat_validate.py --all` passes.
2. `python scripts/cat_resolve_go.py --format json --check-schema` passes.
3. Invalid transitions are blocked.
4. Missing evidence blocks closeout.
5. Scheduled workflows and Windows runners are flagged unless approved.
6. PR template enforces Mission ID and BEAD ID.
7. Agent scorecard updates from a sample closeout.

## Risks

| Risk | Severity | Mitigation |
|---|---:|---|
| Automation loop creates cost | High | cost guard + no schedule default |
| Agent writes outside scope | High | allowed path enforcement |
| False closeout | High | evidence manifest + hashes |
| Registry corruption | Medium | dry-run mode + tests |
| Overengineering | Medium | implement BEADs sequentially |
