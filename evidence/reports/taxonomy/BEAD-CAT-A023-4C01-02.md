# BEAD-CAT-A023-4C01-02 Consumer Adapter Evidence

## Identity

- Mission: `MP-CAT-A023-4C01`
- BEAD: `BEAD-CAT-A023-4C01-02`
- Role: `Builder`
- Observed source HEAD before implementation: `326a25bbf53ca38862fee592c0923bf975d2e02c`
- Artifact HEAD containing the implementation: `2ad14cff6d91d6b591b3b186945831f660450d0d`

## Consumer changes

- `scripts/cat_validate.py` now derives canonical and legacy ID patterns, examples, and the numeric cutover from `gates/CAT_ID_TAXONOMY.yaml`.
- `scripts/cat_new_mission.py` and `scripts/cat_new_bead.py` import the contract-derived patterns and cutover instead of maintaining local regex copies.
- `scripts/cat_mission_id_check.py` uses the contract-derived legacy mission pattern.
- `scripts/cat_align_common.py` exposes `id_matches_taxonomy` for canonical and preserved legacy identity checks.
- The taxonomy contract records preserved example patterns as machine-readable compatibility data.

## Validation

| Gate | Result |
|---|---|
| `python -m pytest tests/test_cat_taxonomy.py tests/test_cat_align_missionid.py -q` | PASS — 30 passed |
| Related generator/validator compatibility suite | PASS — 121 passed |
| `python scripts/cat_check_repo.py` | PASS |
| `python scripts/cat_validate.py --all` | PASS |

## Compatibility result

- New IDs continue to use the canonical mission-stem grammar.
- Grandfathered missions `MP-CAT-000` through `MP-CAT-005` remain accepted.
- Grandfathered BEAD and example forms remain accepted.
- Numeric legacy cutover is read from the contract's declared historical range; no duplicate numeric cutoff is maintained in consumers.
- No historical identifier was renamed.

## Residuals

The contract is now consumed by the validator, generators, ID collision checker, and alignment helper. Gate/template/documentation reconciliation remains A023-03 scope; cross-file asymmetry detection remains A023-04 scope.

