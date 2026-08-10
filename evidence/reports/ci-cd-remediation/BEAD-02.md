# BEAD-CAT-A022-4C01-02 Evidence

## Identity

- Mission: `MP-CAT-A022-4C01`
- BEAD: `BEAD-CAT-A022-4C01-02`
- Exact HEAD: `47d253a5e56311f50b30dbd7cff595140c0638d1`
- Policy version: `1.0.0`

## Changes

- `validate-cat.yml` now checks out full history for exact diff selection.
- Balanced cost guard runs on every validation.
- Strict cost guard runs when workflows, gates, or the guard implementation change.
- Both reports are uploaded as a 14-day artifact.
- Non-control-plane changes receive a deterministic `not_required` strict report.

## Proof gates

- `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate-cat.yml'))"` — **PASS**
- `python -m pytest tests/test_cat_cost_guard.py -q` — **20 passed**
- `python scripts/cat_cost_guard.py --check --tier none --json --output evidence/reports/ci-cd-remediation/BEAD-02.json` — **PASS**, exact-head JSON emitted
- Balanced remains expected to fail until BEAD-03 hardens the seven affected workflows.

## Residual

The normal Balanced CI path is intentionally red on the current baseline because
timeout enforcement is now active. BEAD-03 must remove the seven blocking
timeout findings and the remaining strict warnings.
