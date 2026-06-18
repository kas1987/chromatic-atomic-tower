# CI Governance

## Purpose

CI Governance makes CAT enforceable. It checks that mission contracts, BEAD contracts, state, evidence, tests, and changed-file scope are valid before work is promoted.

## Core Rule

> No CI Pass = No Promotion.

## CI Stages

1. **Repo Integrity** - `cat_check_repo.py`
2. **Schema Validation** - `cat_validate.py --all`
3. **Tower Status** - `cat_status.py`
4. **Evidence Validation** - `cat_evidence.py validate-all`
5. **PR Scope Validation** - `cat_pr_check.py`
6. **Tests** - `pytest -q`
7. **Report Capture** - `cat_ci.py --write-report`

## CI Outputs

CI writes reviewable outputs to:

```text
evidence/ci/reports/
evidence/ci/summaries/
evidence/ci/runs/
```

## Required CI Result

A promoted change must have:

- valid schema checks
- valid BEAD scope
- no forbidden path mutation
- passing tests or documented failure classification
- CI report artifact
- no human gate bypass

## Local Run

```bash
python scripts/cat_ci.py --mode local --write-report
```

## GitHub Actions Run

The workflow file is:

```text
.github/workflows/cat-ci.yml
```

It runs on pull requests and pushes to `main`.
