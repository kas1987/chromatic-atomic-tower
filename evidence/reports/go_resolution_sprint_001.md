# CAT GO Dispatch Packet

Status: ready
Reason: highest-priority approved mission and active BEAD selected

Mission: MP-CAT-001 - Implement CAT State Transition Engine
BEAD: BEAD-CAT-001-001 - Define lifecycle transition matrix
Agent Role: Builder
Autonomy: L3
Confidence: 86 / minimum 75 (high)
Risk: medium
Reversibility: high

## Allowed Paths
- gates/state/**
- docs/architecture/STATE_MACHINE.md
- tests/test_transition_engine.py

## Forbidden Paths
- .env
- infra/prod/**
- secrets/**
- production/**
- deploy/**

## Tool Budget
- search: 1
- read: 6
- write: 5
- execute: 3
- max_runtime_minutes: 30

## Definition of Done
- Mission transitions are explicitly listed.
- BEAD transitions are explicitly listed.
- Terminal states are protected.
- Evidence-required target states are identified.

## Validation
- tests: `pytest -q tests/test_transition_engine.py` -> evidence/test-results/sprint_001_transition_tests.txt

## Stop Conditions
- Required evidence path is missing for a review/completion transition.
- Requested transition is not listed in gates/state/STATE_TRANSITION_RULES.yaml.
- Transition attempts to touch a forbidden path.
- Registry and target contract disagree on mission or BEAD identity.
- Tests fail for reasons inside Sprint 001 scope.
