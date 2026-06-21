# Sprint 002 Plan — Evidence Gate + Closeout Engine

## Executive Summary

Sprint 002 enforces closeout discipline. CAT must not allow BEADs or missions to be completed unless the required evidence exists, validates, and is logged.

## Sprint Goal

Build the CAT evidence gate and closeout engine.

## Core Rule

```text
No Evidence Bundle = No BEAD Completion
No Closeout Report = No Mission Closure
No Learning Note = No Final Done
```

## Active Mission

`MP-CAT-002 — Implement Evidence Gate + Closeout Engine`

## BEAD Queue

1. `BEAD-CAT-002-001` — Define evidence gate rules and bundle schema
2. `BEAD-CAT-002-002` — Implement evidence bundle CLI
3. `BEAD-CAT-002-003` — Implement closeout engine integration
4. `BEAD-CAT-002-004` — Add tests, operator docs, prompts, and closeout checklist

## Deliverables

- `gates/evidence/EVIDENCE_GATE_RULES.yaml`
- `schemas/evidence_bundle.schema.json`
- `scripts/cat_evidence.py`
- `scripts/cat_closeout.py`
- `tests/test_evidence_gate.py`
- `tests/test_closeout_engine.py`
- `docs/operations/EVIDENCE_GATE.md`
- `docs/operations/CLOSEOUT_ENGINE.md`
- `playbooks/EVIDENCE_GATE_PLAYBOOK.md`
- `checklists/EVIDENCE_GATE_CHECKLIST.md`
- `evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml`
- `evidence/bundles/examples/EB-CAT-002-MISSING.yaml`

## Validation

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml
python scripts/cat_closeout.py --type bead --id BEAD-CAT-002-CLOSEOUT-EXAMPLE --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml --to completed --reason "dry-run closeout validation" --dry-run
python scripts/cat_resolve_go.py
pytest -q
```

## Done Criteria

- Evidence bundles validate against schema.
- Required artifact paths are checked.
- Required failed validation blocks closeout.
- Dry-run closeout does not mutate state.
- Apply closeout can delegate to transition engine.
- Audit logs are written.
- Reports are generated.
- Tests pass.
