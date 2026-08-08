# CAT Global Authority Contract

Status: A020-01 draft contract  
Version: 1.0.0  
Canonical machine-readable source: schemas/authority_matrix.schema.json

## Purpose

CAT is the sole global mission and governance authority. A repository or
runtime may execute bounded work and return evidence, but it may not silently
become a second writer of CAT governance state.

## Authority matrix

| Mutable fact | Canonical writer | Canonical path | Consumer policy |
|---|---|---|---|
| Global mission selection | CAT | missions/registry/MISSION_REGISTRY.yaml | CAT only |
| BEAD lifecycle | CAT | scripts/cat_transition.py | CAT only |
| Cross-repo evidence requirements | CAT | evidence/ and gates/ | CAT only |
| Runtime execution evidence | Harness V2 | external:harness-v2/evidence | Evidence returned to CAT |
| Project tree rules | Project Repository | CHROMATIC_TREES.md | Local only; CAT consumes |
| Project execution snapshot | Project Repository | .cat/state.json | Local only; CAT consumes |
| CAT derived state | CAT | state/SPRINT_STATE.md and state/AGENT_HANDOFF_QUEUE.md | Read-only derived output |

Each fact has exactly one canonical writer. Consumers may read, render, cache,
or return evidence under an explicitly bounded contract; they may not write the
canonical path unless a later A020 BEAD explicitly authorizes that operation.

## Cross-repository boundary

CAT may request runtime work from Harness V2 through a versioned adapter
contract. V2 returns execution evidence. V2 does not mutate CAT mission state,
registry state, BEAD lifecycle, or CAT-derived state.

Any future cross-repository mutation must carry:

1. Mission ID;
2. BEAD ID;
3. explicit target paths;
4. validation command and result;
5. evidence destination; and
6. rollback reference.

The mutation gate and generated-state guard are separate later A020 beads.
This document defines their authority boundary; it does not implement them.

## Non-authority rules

- A project adapter is not a global mission writer.
- Runtime telemetry is evidence, not governance state.
- A generated Markdown view is not a competing source of truth.
- V2 implementation topology is outside CAT scope.
- Human approval remains required for promotion and remote mutation.
