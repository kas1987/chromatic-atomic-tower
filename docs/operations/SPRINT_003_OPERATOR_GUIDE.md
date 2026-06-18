# Sprint 003 Operator Guide

## Start Here

Sprint 003 adds CI Governance and bounded self-healing validation.

Run this first:

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_ci.py --mode local --write-report
pytest -q
```

## PR Scope Check

Allowed fixture:

```bash
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_allowed.txt
```

Forbidden fixture:

```bash
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_forbidden.txt
```

The forbidden check should fail.

## Failure Classification

```bash
python scripts/cat_classify_failure.py --check schema --message "schema validation failed"
```

## Self-Healing

```bash
python scripts/cat_self_heal.py --dry-run
```

Apply only after review:

```bash
python scripts/cat_self_heal.py --apply
```

## Closeout Evidence

Use Sprint 003 CI reports as evidence paths in closeout bundles.
