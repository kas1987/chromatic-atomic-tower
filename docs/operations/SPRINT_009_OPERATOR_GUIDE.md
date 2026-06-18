# Sprint 009 Operator Guide

## What You Are Doing

You are not adding a feature. You are correcting CAT's operating truth.

## Commands

```bash
python scripts/cat_registry_audit.py --registry missions/registry/MISSION_REGISTRY.yaml
python scripts/cat_reconcile.py --target docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml --write-report
python scripts/cat_roadmap_sync.py --check
python scripts/cat_align_check.py --strict
pytest -q
```

## Completion Rule

Sprint 009 can close only when reconciliation report and tests pass.

## Next Legal Sprint

`MP-CAT-A010-4C01: GitHub Bridge + PR Governance`
