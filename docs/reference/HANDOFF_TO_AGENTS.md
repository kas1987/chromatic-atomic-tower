# Handoff: CAT GO Automation Completion

## Current Judgment

The repo is architecturally strong and low billing-risk. It should be treated as a
controlled dispatch kernel until state mutation, evidence closeout, GitHub bridge,
and cost guards are fully validated with tests.

## Active Mission

`MP-CAT-GO-AUTO-001`: Complete CAT GO Automation Control Loop.
Status: approved. First BEAD: `BEAD-CAT-GO-001`.

## Starting GO

```bash
# Check alignment
python scripts/cat_state_freshness.py

# Dispatch the first BEAD (queued kickoff)
python scripts/cat_resolve_go.py --allow-queued

# Run baseline validation
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

## BEAD Sequence

| BEAD | Title | Confidence Floor |
|---|---|---|
| BEAD-CAT-GO-001 | State Transition Engine — Validation and Tests | 0.80 |
| BEAD-CAT-GO-002 | BEAD Closeout Enforcement | 0.82 |
| BEAD-CAT-GO-003 | Evidence Manifest Index | 0.78 |
| BEAD-CAT-GO-004 | GitHub Actions Cost Guard | 0.78 |
| BEAD-CAT-GO-005 | GitHub PR and Issue Bridge | 0.76 |
| BEAD-CAT-GO-006 | Agent Scorecard Mutation | 0.75 |
| BEAD-CAT-GO-007 | GO Resolver Dispatch Packet Standard | 0.80 |

## Do Not Do Yet

- Do not enable broad autonomous execution.
- Do not add scheduled GitHub workflows.
- Do not use Windows runners.
- Do not add AI API calls to GitHub Actions.
- Do not let agents auto-close work without evidence.

## Desired End State

A repo where typing `python scripts/cat_resolve_go.py` resolves one valid, scoped,
evidence-bound work packet; execution happens within declared boundaries; validation
and evidence are required; closeout mutates state safely; and agent performance is recorded.
