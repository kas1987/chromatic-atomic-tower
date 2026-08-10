# CAT Global Authority Contract

Status: A020 implementation contract  
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

The mutation gate and generated-state guard are implemented as read-only A020
reference validators. This document defines their authority boundary; neither
validator performs the mutation or state generation it evaluates.

## Portable adapter contract

A CAT consumer uses the versioned schemas `schemas/adapter_config.schema.json`
and `schemas/adapter_state.schema.json`. Both require
`contract_version: "1.0.0"` and `execution_mode: "evidence_only"` for the
configuration contract. A consumer may read the CAT paths explicitly listed
by its adapter and may write only its own explicitly listed project paths.

The adapter's `cat_authority.write_paths` is required to be an empty array.
The same invariant is required in returned execution evidence. Therefore an
adapter can report runtime evidence but cannot claim write authority over the
CAT mission registry, BEAD lifecycle, evidence requirements, or CAT-derived
state. Cross-repository mutation, if ever authorized, must use the separate
A020 mutation-gate contract and carry its own Mission ID, BEAD ID, explicit
paths, validation result, evidence destination, and rollback reference.

Contract-version policy:

- Consumers must reject versions other than `1.0.0` until an explicit
  compatibility agreement is published.
- A future minor version may add optional fields only after schema and
  migration review; it is not implicitly accepted by version `1.0.0`.
- A future major version requires a new adapter contract and migration record.

Returned state must identify the CAT mission, active BEAD (or `null`),
consumer repository, observation time, execution status, evidence path,
validation command, and validation result. This makes the runtime response
traceable evidence rather than a second governance state store.

## Non-authority rules

- A project adapter is not a global mission writer.
- Runtime telemetry is evidence, not governance state.
- A generated Markdown view is not a competing source of truth.
- V2 implementation topology is outside CAT scope.
- Human approval remains required for promotion and remote mutation.
