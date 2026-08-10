# Evidence Report: BEAD-CAT-A023-4C01-01

Mission: `MP-CAT-A023-4C01`
BEAD: `BEAD-CAT-A023-4C01-01`
Role: Cartographer
Contract: `gates/CAT_ID_TAXONOMY.yaml` v2.0.0

## Result

Defined the CAT taxonomy contract and updated the naming document as a thin
projection. The contract preserves historical IDs and makes `priority` the only
urgency axis. `severity`, `complexity`, `risk_level`, `reversibility`, and
`hitl_mode` are independent dimensions. `mission_class` and the compact `4C01`
token are descriptive/non-routing metadata.

## Compatibility decision

Existing numeric priority values remain unchanged. The quick-read projection is
`1→P0`, `2→P1`, `3→P2`, `4→P3`, `5→P4`, where P0 is most urgent. This is a
display compatibility map, not a storage migration. Historical mission and BEAD
IDs are not renamed.

## Consumer inventory

| Surface | Current use | Contract treatment | Follow-on |
|---|---|---|---|
| `missions/registry/MISSION_REGISTRY.yaml` | lookup, queue priority, active pointers | derived index; `priority` remains live urgency | A023-02/03 |
| `missions/**` and `beads/**` | canonical identity/state records | identity writers | A023-02/03 |
| `state/TOWER_STATE.yaml` | active mission/BEAD pointer | derived active-state projection | A023-03 |
| `scripts/cat_resolve_go.py` | priority/status dispatch | use priority/state, never class/compact token | A023-02 |
| `scripts/cat_validate.py` and ID helpers | grammar/schema validation | preserve legacy and current forms | A023-02 |
| `scripts/cat_pr_check.py` / GitHub bridge | PR scope and metadata | PR, branch, head SHA are external relations | A023-03 |
| `schemas/**` | generic ID shape and contract validation | no rewrite in this bead | A023-02 |
| `docs/**` and `gates/**` | guidance and policy | YAML contract wins | A023-03/04 |
| evidence and scorecard writers | provenance and agent history | require exact `head_sha` for observations | A023-04 |
| `docs/architecture/LLM_MODEL_ROUTING.md` | technical C1-C4 complexity axis | separate axis; reconcile later | A023-05 |

## Residual drift

Historical numeric records remain valid. Some records still contain
`priority_tier` and `complexity_order`, and existing scripts/docs contain both
legacy and current examples. This bead records the contract; consumer
canonicalization is intentionally deferred to the remaining A023 beads.

## Validation

```text
python scripts/cat_check_repo.py && python scripts/cat_validate.py --all
PASS
```

The required self-review inventory was run with the BEAD-specified `rg` query
and is captured in the companion JSON report. The evidence snapshot is bound to
the exact current HEAD recorded below. The prior pre-contract snapshot remains
historical context only.

## Exact-head binding

- Observed HEAD: `3a62dc61f865ae5138d6d5a6c88c209f8f3e3748`
- Artifact source HEAD: `3a62dc61f865ae5138d6d5a6c88c209f8f3e3748`
- Prior superseded snapshot: `63fde2482fb83bff48c80a6ac36afa1437267969`

The artifact source HEAD is the immutable repository state read before this
evidence refresh. The evidence commit is a descendant and must not be treated
as the source state being evaluated.

## Handoff

Next: `BEAD-CAT-A023-4C01-02` (Builder), which may update consumers and tests
after preserving the v2 contract and no-renaming compatibility rule.
