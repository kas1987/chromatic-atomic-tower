# Control Planes

The CAT tower separates concerns into four **atomic control planes** so that no
single file type becomes too powerful: a playbook can explain policy, but only a
BEAD controls operational scope. This mirrors the Chromatic Atomic Harness
diagram's **Atomic Control Planes** band. See the
[conformance map](CHROMATIC_ATOMIC_HARNESS_CONFORMANCE.md) for diagram↔repo status.

## Mission Plane — *defines work*

Mission registry, M1–M4 contracts, status + ownership, acceptance criteria.

- `missions/registry/MISSION_REGISTRY.yaml`, `missions/{active,backlog,archived}/`
- Schemas: `schemas/mission.schema.json`, `schemas/mission_registry.schema.json`
- Tools: `scripts/cat_new_mission.py`, `scripts/cat_resolve_go.py`

## Execution Plane — *defines allowed action*

BEAD queue, allowed/forbidden files, tool budgets, stop conditions.

- `beads/{active,completed}/`, dispatch queue
- Schemas: `schemas/bead.schema.json`, `schemas/dispatch_queue_item.schema.json`
- Tools: `scripts/cat_new_bead.py`, `scripts/cat_tool_budget_tracker.py`,
  `scripts/cat_changed_files_guard.py`

## Evidence Plane — *defines proof*

Test results, diff bundles, validation reports, audit trail.

- `evidence/` (logs, reports, bundles, snapshots, `evidence/go/`)
- Schemas: `schemas/evidence.schema.json`, `schemas/evidence_bundle.schema.json`
- Tools: `scripts/cat_evidence.py`, `scripts/cat_generate_evidence_bundle.py`

## Learning Plane — *defines improvement*

Decision logs, incident learnings, agent scorecards, pattern library.

- `learnings/DECISION_LOG.md`, `learnings/INCIDENT_LOG.md`,
  `learnings/PATTERN_LIBRARY.md`, `learnings/ECHO_LOG.md`
- `agents/registry/AGENT_SCORECARD.yaml` (+ `scripts/cat_agent_scorecard.py`)

## Plane Processing Flow

The diagram's plane flow — **Collect → Normalize → Correlate → Score → Validate
→ Learn → Recommend** — is realised by the LOGHOUSE pipeline, which feeds the
Evidence and Learning planes:

| Step | Implementation |
|------|----------------|
| Collect | raw log/evidence ingest (`scripts/cat_loghouse.py`) |
| Normalize | `scripts/loghouse/normalize.py` (telemetry envelopes) |
| Correlate | `scripts/loghouse/correlate.py` (time windows, deploy events) |
| Score / Validate | `scripts/loghouse/rules.py`, `scripts/cat_score_confidence.py` |
| Learn | `learnings/` + `agents/registry/AGENT_SCORECARD.yaml` |
| Recommend | `scripts/cat_resolve_go.py`, dispatch emission |

## Why four planes

The planes prevent one type of file from becoming too powerful. A playbook can
explain policy, but a BEAD controls operational scope; evidence proves outcomes,
but only the Learning plane changes future behaviour. This separation is what
makes the governance rules (No Mission = No Work, No Evidence = No Closeout, …)
enforceable rather than advisory.
