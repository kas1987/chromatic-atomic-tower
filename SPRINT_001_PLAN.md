# SPRINT-001 Plan — CAT State Transition Engine

## Goal

Make CAT lifecycle state movement executable, auditable, and testable.

## Sprint BEADs

| Order | BEAD | Owner | Result |
|---:|---|---|---|
| 1 | BEAD-CAT-001-001 | Builder | Transition matrix finalized |
| 2 | BEAD-CAT-001-002 | Builder | CLI implemented |
| 3 | BEAD-CAT-001-003 | Reviewer | Tests and schema checks added |
| 4 | BEAD-CAT-001-004 | Scribe | Operator docs and closeout evidence |

## Validation Commands

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_resolve_go.py
python scripts/cat_transition.py --type bead --id BEAD-CAT-001-001 --to in_progress --reason "dry-run validation" --evidence evidence/reports/sprint_001_transition_dry_run.md --dry-run
pytest -q
```

## Completion Rule

Sprint 001 is not complete until CAT can deny invalid transitions and allow valid dry-runs with a clear audit record.
