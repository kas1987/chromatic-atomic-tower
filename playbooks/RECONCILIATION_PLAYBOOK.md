# Reconciliation Playbook

## Purpose

This playbook governs how CAT reconciles live repository state against canonical mission truth.

## Core Rule

```text
No Reconciled Registry = No New Sprint
```

## Standard Loop

```text
Observe -> Compare -> Classify Drift -> Patch State -> Validate -> Record Evidence -> Queue Next
```

## Inputs

| Input | Required |
|---|---:|
| `missions/registry/MISSION_REGISTRY.yaml` | Yes |
| `CAT_ROADMAP.md` | Yes |
| `state/SPRINT_STATE.md` | Yes |
| `docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml` | Yes |

## Drift Classes

| Drift | Meaning | Response |
|---|---|---|
| Registry Drift | Registry active mission/status wrong | Patch registry |
| Roadmap Drift | Roadmap names old sprint sequence | Patch roadmap |
| BEAD Drift | Active BEAD no longer matches active mission | Move or close stale BEAD |
| Evidence Drift | Claim exists without report | Generate report or block closeout |
| Backlog Drift | Future missions missing | Scaffold backlog mission packets |

## Stop Conditions

Stop if reconciliation would mutate secrets, production infra, external systems, or unrelated repos.

## Sprint 009 Active Mission

During Sprint 009, `active_mission_id` must be `MP-CAT-A009-4C01` until closeout.

## References

- [SPRINT_009_OPERATOR_GUIDE.md](../docs/operations/SPRINT_009_OPERATOR_GUIDE.md)
- [LIVE_REPO_ALIGNMENT_TARGET.yaml](../docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml)
- [RECONCILIATION_CHECKLIST.md](../checklists/RECONCILIATION_CHECKLIST.md)
