# CAT Roadmap

## Sprint 000: Core Foundation

Status: packaged baseline.

Goal: establish the repo, mission registry, BEAD contracts, gates, schemas, validators, GO resolver MVP, prompts, docs, and checklists.

## Sprint 001: State Transition Engine

Goal: enforce mission and BEAD transitions.

Deliverables:

- `scripts/cat_transition.py`
- transition rules YAML
- status mutation tests
- automatic registry updates
- blocked/escalated/incident handling

## Sprint 002: Evidence Index

Goal: make proof queryable.

Deliverables:

- evidence manifest
- evidence schema enforcement
- closeout report generator
- validation artifact lookup

## Sprint 003: GitHub Bridge

Goal: connect Mission -> BEAD -> Branch -> PR.

Deliverables:

- issue template enforcement
- PR title checker
- commit message checker
- CODEOWNERS alignment

## Sprint 004: Agent Scorecard Automation

Goal: promote/demote agents based on measured behavior.

Deliverables:

- score mutation rules
- incident penalty model
- tool-budget tracking
- model-routing adjustments

## Sprint 005: CAT Portable Project Adapter

Goal: let any repo adopt CAT with a `.cat/` adapter folder.

Deliverables:

- project adapter schema
- bootstrap script
- minimal project registry
- sync rules
