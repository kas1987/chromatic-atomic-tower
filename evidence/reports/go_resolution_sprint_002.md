# CAT GO Dispatch Packet

Status: ready
Reason: highest-priority approved mission and active BEAD selected

Mission: MP-CAT-002 - Implement CAT Evidence Gate and Closeout Engine
BEAD: BEAD-CAT-002-001 - Define evidence gate rules and bundle schema
Agent Role: Builder
Autonomy: L3
Confidence: 88 / minimum 78 (high)
Risk: medium
Reversibility: high

## Allowed Paths
- gates/evidence/**
- schemas/evidence_bundle.schema.json
- docs/operations/EVIDENCE_GATE.md
- tests/test_evidence_gate.py

## Forbidden Paths
- .env
- infra/prod/**
- secrets/**
- production/**
- deploy/**

## Tool Budget
- search: 1
- read: 5
- write: 5
- execute: 3
- max_runtime_minutes: 30

## Definition of Done
- Evidence gate rules exist.
- Evidence bundle schema exists.
- Passing and failing evidence examples are defined.
- Evidence rules explain required validation behavior.

## Validation
- schema: `python scripts/cat_validate.py --all` -> evidence/reports/schema_validation_sprint_002.md

## Stop Conditions
- Evidence requirements conflict with existing mission or BEAD schemas.
- Evidence bundle cannot reference mission and BEAD IDs clearly.
- Required artifact path behavior is ambiguous.
- Tests fail for reasons inside Sprint 002 scope.
