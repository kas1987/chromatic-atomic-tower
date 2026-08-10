# BEAD-CAT-A023-4C01-06 Routing Contract Evidence

## Identity

- Mission: `MP-CAT-A023-4C01`
- BEAD: `BEAD-CAT-A023-4C01-06`
- Role: `Cartographer`
- Evidence type: contract and deterministic matrix validation
- Observed source HEAD before implementation: `a04570b056c2195072c1048f5605411afdf74db5`
- Artifact HEAD containing the implementation: `9d34d22b8ff9f8c06789b9b2863ef9d1315178d4`

## Artifacts

- `schemas/route_decision.schema.json`
- `schemas/lifecycle_event.schema.json`
- `gates/ROUTE_DECISION_POLICY.yaml`
- `tests/test_cat_route_matrix.py`

## Validation

| Gate | Result |
|---|---|
| `python -m pytest tests/test_cat_route_matrix.py -q` | PASS — 17 passed |
| `python scripts/cat_check_repo.py` | PASS |
| `python scripts/cat_validate.py --all` | PASS |
| `git diff --check` for the bead files | PASS |

## Contract findings

- Route outcomes are limited to `allow_plan`, `require_human`, and `block`.
- Effects are limited to `none` and `dry_run`; no route result authorizes mutation.
- Stale HEAD, malformed output, and dependency cycles fail closed with `block`.
- Budget exhaustion, provider outage, policy drift, conflicting fields, and human-only control require a human gate.
- Duplicate delivery is represented by an idempotency key and returns the original decision without mutation.
- Lifecycle state is a distinct field from taxonomy classification and complexity.
- Evidence carries independent observed and artifact HEAD SHAs.
- Agent or model output is represented as an observation and cannot satisfy human approval.

## Residuals

Runtime transition integration, self-healing execution, provider/model routing, and remote repository settings remain intentionally deferred by the active BEAD. The existing transition engine's deferred guard evaluation is not changed by this contract-only slice.

