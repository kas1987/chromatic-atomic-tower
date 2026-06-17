# PDR-CAT-001 — Implement CAT State Transition Engine

## Executive Summary

Sprint 001 turns Chromatic Atomic Tower from a validated repo kernel into an executable lifecycle system. The critical deliverable is a deterministic state transition engine that moves missions and BEADs only through approved states, records evidence, updates registry/tower state, and writes an audit trail.

## Problem

Sprint 000 established contracts, folders, validation, and GO-mode resolution. However, status movement is still mostly manual. Manual lifecycle movement creates drift risk:

- mission status may differ from registry status
- BEAD status may differ from tower state
- agents may mark work complete without evidence
- terminal states may be reopened casually
- audit history may be missing

## Decision

Build `scripts/cat_transition.py` and supporting rules as the canonical transition path.

The engine must support:

1. mission transitions
2. BEAD transitions
3. dry-run validation
4. denied transition reasons
5. evidence-required targets
6. JSONL audit events
7. mission registry updates
8. tower state updates
9. terminal-state protections
10. tests and operator documentation

## Scope

### In Scope

- `gates/state/STATE_TRANSITION_RULES.yaml`
- `scripts/cat_transition.py`
- `scripts/cat_status.py`
- `schemas/transition_event.schema.json`
- transition tests
- Sprint 001 mission and BEAD contracts
- state-transition playbook and operator guide

### Out of Scope

- GitHub API automation
- remote branch mutation
- production deployment
- credential handling
- cross-repo orchestration

## State Philosophy

A mission or BEAD does not move because an agent says it moved. It moves because a permitted transition occurred and left evidence.

```text
Current State + Target State + Rule + Evidence + Actor + Reason = Transition Event
```

## Success Criteria

- `python scripts/cat_validate.py --all` passes.
- `pytest -q` passes.
- `python scripts/cat_resolve_go.py` selects `BEAD-CAT-001-001`.
- Dry-run transition command returns allowed without mutating files.
- Invalid transition command returns denied and records an audit event.

## Risk Assessment

| Risk | Level | Mitigation |
|---|---:|---|
| Bad transition mutates lifecycle state | High | Dry-run, tests, explicit rules |
| Completion without evidence | Medium | Evidence-required target states |
| Registry drift | Medium | Transition script updates registry |
| Tower state drift | Medium | Transition script updates tower state |
| Terminal-state reopening | High | Terminal transitions denied by default |

## Rollback

Revert the Sprint 001 files and restore Sprint 000 state. Preserve `evidence/logs/transitions.jsonl` for incident review.

## Definition of Done

- Transition rules exist and are documented.
- Transition CLI works in dry-run and apply mode.
- Tests pass.
- Schema validation passes.
- Operator guide exists.
- Evidence and learning logs are updated.
