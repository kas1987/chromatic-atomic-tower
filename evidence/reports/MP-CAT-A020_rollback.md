# A020 Rollback Record

Mission: `MP-CAT-A020-4C01`
Stabilized baseline: A019 closeout reference `c50b79dd0e49950024cc7e18d60c2f769d1b1ac5`

## Reversible procedure

1. Keep PR #48 and its branch available for audit; do not merge or delete it.
2. Revert the A020-specific contract artifacts and lifecycle records using the
   transition snapshots recorded under `evidence/snapshots/`.
3. Restore the A019 mission/bead/evidence state from the A019 closeout reference
   and confirm `python scripts/cat_check_repo.py` plus
   `python scripts/cat_validate.py --all` pass.
4. Re-run the A019 closeout evidence gate before any successor promotion.

## A020-specific artifacts covered

- `docs/architecture/CAT_GLOBAL_AUTHORITY_CONTRACT.md`
- `schemas/authority_matrix.schema.json`
- `schemas/adapter_config.schema.json`
- `schemas/adapter_state.schema.json`
- `schemas/cross_repo_mutation.schema.json`
- `schemas/derived_state_ownership.schema.json`
- `scripts/cat_cross_repo_gate.py`
- `scripts/cat_state_ownership_guard.py`
- A020 contract tests and `evidence/reports/MP-CAT-A020_*`

This record is a rollback plan and evidence reference; it does not execute a
rollback or mutate PR #47.
