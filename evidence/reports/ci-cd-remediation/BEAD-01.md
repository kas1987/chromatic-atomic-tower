# BEAD-CAT-A022-4C01-01 Evidence

## Identity

- Mission: `MP-CAT-A022-4C01`
- BEAD: `BEAD-CAT-A022-4C01-01`
- Exact HEAD: `47d253a5e56311f50b30dbd7cff595140c0638d1`
- Policy: `gates/ci/COST_GUARD_POLICY.yaml`, version `1.0.0`
- Evaluated workflows: 8

## Deterministic tier results

| Tier | Result | Findings |
|---|---|---:|
| None | PASS / observe-only | 17 warnings, 0 blocking failures |
| Balanced | FAIL before hardening | 7 blocking timeout findings, 10 warnings |
| Strict | FAIL before hardening | 17 blocking findings |

The baseline is expected: Balanced blocks unsafe/material cost controls and
timeouts, while permissions and concurrency remain advisory until workflow
hardening is complete. Strict promotes all five policy rules to blocking.

## Proof gates

- `python -m pytest tests/test_cat_cost_guard.py -q` — **19 passed**
- `python scripts/cat_cost_guard.py --check --tier none --json --output evidence/reports/ci-cd-remediation/BEAD-01.json` — **PASS**, exact-head JSON emitted
- `python scripts/cat_cost_guard.py --check --tier balanced` — **FAIL as expected**, 7 blocking findings before hardening
- `python scripts/cat_cost_guard.py --check --tier strict` — **FAIL as expected**, 17 blocking findings before hardening

## Contract decisions

- CLI tier overrides `CAT_COST_GUARD_TIER`.
- Environment tier overrides the versioned policy default (`balanced`).
- Legacy `--strict` remains an alias for `--tier strict`.
- Invalid policy, invalid YAML, unreadable workflows, and invalid job mappings
  are evaluator errors and return exit code 2.
- No schedule or risky-runner safety rule was weakened.
