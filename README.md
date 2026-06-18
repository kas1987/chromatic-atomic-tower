# Chromatic Atomic Tower - Sprint 003 Pro GPT Package

Chromatic Atomic Tower (CAT) is the governance kernel for Chromatic Atomic Harness. Sprint 003 adds the **CI Governance and Self-Healing Validation Engine**.

## Current Sprint

**Sprint 003: CI Governance and Self-Healing Validation**

Core rule:

> No CI Pass = No Promotion.

## What This Package Contains

- Mission Pack: `missions/active/MP-CAT-003_CI_GOVERNANCE_SELF_HEALING.yaml`
- PDR: `PDR_CAT_003_CI_GOVERNANCE_SELF_HEALING.md`
- Sprint Plan: `SPRINT_003_PLAN.md`
- CI rules: `gates/ci/CI_GOVERNANCE_RULES.yaml`
- GitHub Actions workflow: `.github/workflows/cat-ci.yml`
- PR scope checker: `scripts/cat_pr_check.py`
- CI local runner: `scripts/cat_ci.py`
- Failure classifier: `scripts/cat_classify_failure.py`
- Self-heal validator: `scripts/cat_self_heal.py`
- CI report schemas and tests
- Operator guide, playbook, checklist, and Pro GPT prompt

## Quick Validation

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_ci.py --mode local --write-report
pytest -q
```

## Sprint 003 Commands

```bash
python scripts/cat_resolve_go.py
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_allowed.txt
python scripts/cat_self_heal.py --dry-run
python scripts/cat_classify_failure.py --check schema --message "schema validation failed"
```

## Operating Rule

Self-healing may repair structure. It may not repair truth.
