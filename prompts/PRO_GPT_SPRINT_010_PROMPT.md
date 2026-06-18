# Sprint 010 — GitHub Bridge Builder Prompt

Mission: MP-CAT-A010-4C01
Role: Builder

Execute only the active BEAD returned by `python scripts/cat_resolve_go.py`.

Rules:
- Touch only BEAD allowed_paths.
- Never touch forbidden_paths.
- Use A-tier Mission and BEAD IDs in all GitHub metadata.
- Emit evidence under evidence/github/reports when validation commands support --write-report.

Validation examples:

```bash
python scripts/cat_git_bridge.py validate-pr \
  --title "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --branch feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract \
  --commit-message "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --bead beads/active/BEAD-CAT-A010-4C01-01.yaml \
  --changed-files tests/fixtures/github/changed_files_allowed.txt
```
