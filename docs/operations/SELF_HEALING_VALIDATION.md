# Self-Healing Validation

## Purpose

Self-healing validation repairs safe structural problems without pretending to fix logic, security, evidence, or architecture.

## Safe Repairs

Allowed:

- create required empty evidence folders
- create `.gitkeep` placeholders
- create missing CI output directories
- regenerate CI summary from existing checks
- normalize generated report paths

## Forbidden Repairs

Blocked:

- secrets
- production configuration
- deployment files
- mission state transitions
- evidence fabrication
- test result fabrication
- application logic changes
- architecture decisions

## Dry-Run First

Always run:

```bash
python scripts/cat_self_heal.py --dry-run
```

Only apply after reviewing the plan:

```bash
python scripts/cat_self_heal.py --apply
```

## Rule

> Self-healing repairs structure, not truth.
