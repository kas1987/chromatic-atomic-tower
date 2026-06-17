# Sprint 001 Operator Guide

## Purpose

Sprint 001 gives CAT a safe state-transition engine. Use this guide to validate, dry-run, apply, and audit mission/BEAD status movement.

## Standard Workflow

```text
Resolve GO -> inspect BEAD -> dry-run transition -> implement work -> validate -> apply transition -> record evidence -> queue next BEAD
```

## Commands

### Check repo

```bash
python scripts/cat_check_repo.py
```

### Validate contracts

```bash
python scripts/cat_validate.py --all
```

### Resolve next GO dispatch

```bash
python scripts/cat_resolve_go.py
```

### Dry-run a BEAD transition

```bash
python scripts/cat_transition.py --type bead --id BEAD-CAT-001-001 --to in_progress --reason "start transition matrix work" --dry-run
```

### Apply a BEAD transition with evidence

```bash
python scripts/cat_transition.py --type bead --id BEAD-CAT-001-001 --to validating --reason "transition matrix complete" --evidence evidence/reports/bead_cat_001_001_transition_matrix.md
```

### Show CAT status

```bash
python scripts/cat_status.py
```

## Operator Discipline

Do not hand-edit lifecycle statuses unless fixing a broken transition engine under explicit human direction. Status edits are governance mutations.
