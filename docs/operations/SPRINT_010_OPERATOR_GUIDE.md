# Sprint 010 Operator Guide

## Quick Validation

```bash
python scripts/cat_git_bridge.py validate-pr \
  --title "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --branch feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract \
  --commit-message "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --bead beads/active/BEAD-CAT-A010-4C01-01.yaml \
  --changed-files tests/fixtures/github/changed_files_allowed.txt \
  --write-report
```

## Human Gate

Do not mutate branch protection, repository settings, secrets, deployments, or production environments without explicit human approval.
