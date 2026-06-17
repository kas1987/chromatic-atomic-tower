# PDR CAT 004: V2 Alignment Guards

## Status

Approved for Sprint 004.

## Context

CAT has completed the foundation, state transition engine, evidence closeout engine, and CI governance/self-healing validation MVP. A read-only review of `C:/Users/kas41/chromatic-harness-v2` showed several mature operating practices that can strengthen CAT without importing v2's full runtime surface.

The strongest practices are:

- pre-session unified guard;
- GO decision record before mutation;
- state freshness and drift checks;
- dry-run branch governance;
- dry-run root artifact hygiene;
- activity/backlog lanes;
- budget and provider burn evidence.

## Decision

Sprint 004 will adopt only the compact guard patterns needed to make CAT's Tower state more reliable:

1. v2-to-CAT alignment matrix.
2. Tower state freshness guard.
3. Dry-run branch and root hygiene checks.
4. Unified Tower guard report and operator docs.

Sprint 004 will defer lane-aware backlog and budget telemetry to a later mission. It will reject bulk v2 folder migration, visual control plane work, and autonomous merge behavior.

## Rationale

CAT's core value is a small, auditable mission -> BEAD -> evidence kernel. v2's best practices should become CAT-native checks, not imported sprawl. The immediate risk observed in CAT is stale Tower state after MP-CAT-003 reached `learned`, so state freshness belongs first.

## Scope

In scope:

- alignment documentation;
- local read-only validators;
- durable guard evidence;
- tests for pass/fail behavior;
- operator documentation.

Out of scope:

- modifying `chromatic-harness-v2`;
- MCP/server configuration;
- visual console work;
- automatic repair;
- branch deletion or pruning;
- automatic merge.

## BEAD Plan

| BEAD | Title | Output |
|---|---|---|
| BEAD-CAT-004-001 | Create v2-to-CAT alignment matrix | PDR and alignment matrix |
| BEAD-CAT-004-002 | Implement Tower state freshness guard | `scripts/cat_state_freshness.py` and tests |
| BEAD-CAT-004-003 | Add branch and root hygiene checks | hygiene gates, script, tests |
| BEAD-CAT-004-004 | Add unified Tower guard report and docs | `scripts/cat_tower_guard.py`, schema, docs, report |

## Validation

Required validation for Sprint 004:

```bash
python scripts/cat_validate.py --all
python scripts/cat_tower_guard.py --write-report
pytest -q
```

BEAD-CAT-004-001 requires only schema validation and full tests because it is documentation and mission packet setup.

## Risks

| Risk | Mitigation |
|---|---|
| v2 migration sprawl | Adopt documented patterns only; reject folder topology and visual console work. |
| accidental mutation | All Sprint 004 guards are report-only by default. |
| stale state false positives | Tests will cover terminal mission/BEAD cases and active registry consistency. |
| PR scope creep | BEAD allowed paths isolate documentation, state freshness, hygiene, and guard integration. |

## Rollback

Revert MP-CAT-004 mission, BEADs, alignment docs, guard scripts, schemas, tests, and Sprint 004 generated evidence. Preserve evidence already used by human review if applicable.
