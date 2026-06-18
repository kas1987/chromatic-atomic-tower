# PDR-CAT-A010: GitHub Bridge + PR Governance Engine

## Executive Decision

Build Sprint 010 as the first external enforcement layer for CAT. Sprints 000 through 009 established the repo foundation, state machine, evidence/closeout, CI governance, reconciliation, and mission registry alignment. Sprint 010 connects those internal controls to GitHub so branches, PRs, commits, issue intake, changed files, and CI status are governed by Mission Packs and BEADs.

## Problem

CAT can validate internal mission artifacts, but live repository work can still bypass the tower if GitHub metadata does not carry Mission and BEAD identifiers. A PR without traceability becomes orphan work. A branch without a Mission ID becomes context debt. A changed file outside a BEAD becomes scope creep.

## Core Rule

```text
No GitHub Mutation = No Mission + BEAD Trace
```

## Scope

In scope:

- Branch naming rules
- PR title rules
- Commit message rules
- Changed-file scope validation
- Issue-to-mission intake scaffolding
- GitHub Bridge CI workflow
- Evidence report generation
- Operator guide, playbook, checklist, tests

Out of scope:

- Repository settings mutation
- Branch protection mutation
- Secret scanning configuration mutation
- Production deployment
- Automatic merge behavior

## Design

Sprint 010 adds a GitHub Bridge plane between GitHub activity and CAT governance.

```text
Issue / Branch / Commit / PR
  -> GitHub Bridge Validator
  -> Mission Pack + BEAD Lookup
  -> Changed File Scope Guard
  -> CI Governance
  -> Evidence Report
  -> Review / Closeout
```

## Acceptance Criteria

- PR title includes `[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01]` (A-tier) or grandfathered legacy tokens.
- Branch name includes mission and BEAD identifiers in lowercase slug form.
- Commit messages include both Mission and BEAD tokens.
- Changed files match the selected BEAD `allowed_paths`.
- Forbidden paths always fail validation.
- Issue intake can produce a draft Mission Pack candidate.
- CI can run GitHub Bridge validation locally.
- Evidence reports are generated under `evidence/github/reports`.

## Validation

```bash
python scripts/cat_git_bridge.py validate-pr --title "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" --branch feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract --commit-message "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" --bead beads/active/BEAD-CAT-A010-4C01-01.yaml --changed-files tests/fixtures/github/changed_files_allowed.txt --write-report
python scripts/cat_branch_name.py validate feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract
python scripts/cat_changed_files_guard.py --bead beads/active/BEAD-CAT-A010-4C01-01.yaml --changed-files tests/fixtures/github/changed_files_allowed.txt
python scripts/cat_issue_intake.py --issue-json tests/fixtures/github/issue_intake.json --output-dir /tmp/cat-intake-test
python -m pytest -q tests/test_git_bridge.py tests/test_branch_name.py tests/test_changed_files_guard.py tests/test_issue_intake.py
```

## Definition of Done

Sprint 010 is complete when GitHub activity cannot be considered CAT-compliant unless it carries a valid Mission ID, valid BEAD ID, valid changed-file scope, and a generated validation report.
