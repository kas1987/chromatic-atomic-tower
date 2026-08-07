# CI Governance

## Purpose

CI Governance makes CAT enforceable. It checks that mission contracts, BEAD contracts, state, evidence, tests, and changed-file scope are valid before work is promoted.

## Core Rule

> No CI Pass = No Promotion.

## Default Branch

CAT's default branch is `master`. Workflow push triggers should target `master` (not `main`).

## CI Stages

1. **Repo Integrity** - `cat_check_repo.py`
2. **Schema Validation** - `cat_validate.py --all`
3. **Tower Status** - `cat_status.py`
4. **Evidence Validation** - `cat_evidence.py validate-all`
5. **PR Scope Validation** - `cat_pr_check.py`
6. **Tests** - `pytest -q`
7. **Report Capture** - `cat_ci.py --write-report`

## Check Tiers

| Tier | Checks | Merge impact |
|---|---|---|
| **Required** | `validate` (`validate-cat.yml`), `cat-ci` (`cat-ci.yml`) | Must pass before promotion |
| **Advisory** | `governance-ci`, `loghouse-ci`, `github-bridge`, `codex-review` | Informational; do not block merge while advisory |

### Required

- **validate** — `Validate CAT` workflow (`.github/workflows/validate-cat.yml`). Includes repo checks, hygiene, GO resolve, pytest, and `cat_cost_guard` (see below).
- **cat-ci** — `CAT CI Governance` workflow (`.github/workflows/cat-ci.yml`). Stages above plus CI report artifacts.

### Advisory

- **governance-ci** — CAT Governance CI / harness alignment
- **loghouse-ci** — LOGHOUSE pipeline and drift gates
- **github-bridge** — GitHub Bridge sample validation
- **codex-review** — Codex PR review (replaces retired Claude Code Review; advisory until stability window)

## Cost Guard

`scripts/cat_cost_guard.py --check` runs inside `validate-cat.yml` (required `validate` job). New workflows that violate budget/runner rules fail this check. See `docs/github_actions_guardrails.md`.

## Review Automation

| Status | Workflow | Notes |
|---|---|---|
| Retired | Claude Code Review | Removed from `pull_request` due to OAuth/plugin flake; no longer a review signal |
| Active (advisory) | Codex Review (`codex-review.yml`) | Uses `openai/codex-action` on `pull_request`; advisory until a stability window is complete |

See `docs/operations/PR_REVIEW_WORKFLOW.md` for the review chain and settle windows.

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
- required checks (`validate`, `cat-ci`) green

## Local Run

```bash
python scripts/cat_ci.py --mode local --write-report
```

## GitHub Actions Run

Primary required workflow files:

```text
.github/workflows/validate-cat.yml
.github/workflows/cat-ci.yml
```

They run on pull requests and pushes to `master`.
