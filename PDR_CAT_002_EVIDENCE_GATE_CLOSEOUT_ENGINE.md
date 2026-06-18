# PDR-CAT-002 — Evidence Gate + Closeout Engine

## Executive Summary

Sprint 002 turns CAT evidence from a documentation habit into an enforceable lifecycle gate.

The core operating rule is:

```text
No Evidence Bundle = No BEAD Completion
No Closeout Report = No Mission Closure
No Learning Note = No Final Done
```

Sprint 001 made state transitions executable. Sprint 002 makes completion trustworthy by requiring evidence bundles, validation results, closeout reports, audit logs, and learning notes before BEADs or missions can be closed.

---

## 1. Mission Metadata

| Field | Value |
|---|---|
| PDR ID | PDR-CAT-002 |
| Mission ID | MP-CAT-002 |
| Sprint | SPRINT-002 |
| Title | Evidence Gate + Closeout Engine |
| Level | M3 Complex |
| Owner | Human Owner |
| Status | Active |
| Risk | Medium |
| Reversibility | High |
| Autonomy | L3 |
| Confidence Minimum | 78 |

---

## 2. Problem Statement

CAT can validate contracts and move lifecycle states, but completion is still too easy to claim if evidence is only loosely referenced.

Without a strict evidence gate, agents can:

- mark BEADs complete without real proof;
- transition missions to reviewed or closed without validation artifacts;
- lose test output, diffs, decision notes, and audit traces;
- skip learnings that should improve the Harness;
- create orphan reports that are not attached to Mission/BEAD IDs.

Sprint 002 closes that gap.

---

## 3. Design Objective

Create a deterministic closeout path that verifies evidence before final lifecycle movement.

The system must answer:

1. What evidence is required for this BEAD or mission?
2. Does each required artifact exist?
3. Did validation pass?
4. Is a closeout report generated?
5. Is the closeout event logged?
6. Can the transition safely proceed?

---

## 4. Scope

### In Scope

- Evidence gate rules.
- Evidence bundle schema.
- Evidence bundle creation and validation CLI.
- Closeout CLI for BEADs and missions.
- Integration with Sprint 001 transition engine.
- Closeout reports.
- Closeout JSONL audit log.
- Tests for evidence validation and closeout behavior.
- Operator documentation and playbooks.

### Out of Scope

- GitHub PR comment automation.
- External artifact uploads.
- Remote CI log ingestion.
- Production deployments.
- Secrets handling.
- Multi-repo closeout orchestration.

---

## 5. Operating Rules

| Rule | Meaning |
|---|---|
| No Evidence Bundle = No BEAD Completion | BEAD `completed` requires a valid evidence bundle. |
| No Required Artifact = No Closeout | All required evidence paths must exist. |
| Failed Required Validation = No Completion | Required validations must pass unless explicitly marked non-blocking. |
| No Learning Note = No Mission Closure | Mission closeout must include a learning note. |
| No Audit Event = No Done | Every closeout attempt is written to audit logs. |
| Dry Run First | Operators can test closeout without mutation. |

---

## 6. Architecture

```text
Mission / BEAD Contract
  -> Evidence Requirements
    -> Evidence Bundle
      -> Evidence Gate Validation
        -> Closeout Report
          -> State Transition
            -> Closeout Audit Log
              -> Learning Update
```

### New Control Files

```text
gates/evidence/EVIDENCE_GATE_RULES.yaml
schemas/evidence_bundle.schema.json
scripts/cat_evidence.py
scripts/cat_closeout.py
docs/operations/EVIDENCE_GATE.md
docs/operations/CLOSEOUT_ENGINE.md
playbooks/EVIDENCE_GATE_PLAYBOOK.md
checklists/EVIDENCE_GATE_CHECKLIST.md
```

---

## 7. Evidence Bundle Model

A valid bundle must include:

- evidence ID;
- mission ID;
- optional BEAD ID;
- target type;
- validation result;
- required artifacts;
- supporting artifacts;
- summary;
- learning note;
- closeout readiness.

The bundle must validate against `schemas/evidence_bundle.schema.json`.

---

## 8. Closeout Flow

```text
1. Operator or agent creates evidence bundle.
2. CAT validates bundle schema.
3. CAT checks required artifact paths.
4. CAT checks required validation result.
5. CAT writes closeout report.
6. CAT dry-runs or applies transition.
7. CAT writes closeout audit event.
8. CAT preserves learning note.
```

---

## 9. Acceptance Criteria

- Evidence gate rules are explicit and machine-readable.
- Evidence bundle schema is included and validated.
- `cat_evidence.py` can create and validate evidence bundles.
- `cat_closeout.py` can dry-run BEAD closeout.
- `cat_closeout.py` can apply BEAD closeout through the transition engine.
- Missing required artifacts block completion.
- Failed required validation blocks completion.
- Closeout reports are written to `evidence/reports/`.
- Closeout attempts are written to `evidence/logs/closeouts.jsonl`.
- Tests cover passed, failed, missing evidence, and dry-run behavior.
- Operator guide explains safe usage.

---

## 10. Validation Plan

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml
python scripts/cat_closeout.py --type bead --id BEAD-CAT-002-001 --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml --to completed --reason "dry-run closeout validation" --dry-run
python scripts/cat_resolve_go.py
pytest -q
```

---

## 11. Rollback Plan

Rollback is simple because Sprint 002 is file-local and state-local.

Revert:

- `gates/evidence/**`
- `schemas/evidence_bundle.schema.json`
- `scripts/cat_evidence.py`
- `scripts/cat_closeout.py`
- Sprint 002 mission and BEAD contracts
- Sprint 002 docs, playbooks, prompts, tests, and evidence examples

Preserve audit logs if any real closeout events were applied.

---

## 12. Definition of Done

- All schema validation passes.
- All tests pass.
- Example bundle validates.
- Dry-run closeout succeeds.
- Missing-artifact closeout fails.
- GO resolver selects Sprint 002 BEAD.
- Operator instructions are complete.
- Sprint package is zipped and ready for repo use.
