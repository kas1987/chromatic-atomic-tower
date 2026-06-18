# PDR-CAT-A009: Repo Alignment and Mission Packet Reconciliation

## 1. Executive Summary

CAT has reached the point where its live repository state, packaged sprint artifacts, and mission registry must be reconciled before additional feature expansion. Sprint 009 creates the reconciliation mission, enforcement rules, scripts, tests, and operator instructions necessary to align the live repo with CAT's true sprint lineage.

## 2. Problem Statement

The live repo can drift from generated packages and actual project intent. The repository completed missions through MP-CAT-A008-4C01, but CAT_ROADMAP.md still described Sprint 003 as current and omitted later sprint work.

This creates operational risk:

- GO resolver may pick stale BEADs.
- Registry may point to the wrong active mission.
- Roadmap may name old sprint intentions.
- Future Mission Packs may be built on stale assumptions.
- Agent scorecards may be created from invalid event lineage.

## 3. Decision

Create Sprint 009 as an explicit reconciliation sprint before MP-CAT-A010 GitHub Bridge work.

Decision statement:

```text
Before CAT expands, CAT must reconcile itself.
```

## 4. Goals

- Create a formal Mission Pack for reconciliation (`MP-CAT-A009-4C01`).
- Define canonical sprint lineage from 000 through 009.
- Update mission registry to reflect actual state.
- Add reconciliation target rules and scripts.
- Add tests to prevent roadmap/registry drift.
- Produce evidence reports for auditability.
- Scaffold backlog missions A010 through A012.

## 5. Non-Goals

- Do not implement GitHub Bridge yet.
- Do not implement agent scoring automation yet.
- Do not execute multi-model coding dispatch yet.
- Do not mutate secrets, environment files, production configs, or infrastructure.
- Do not rename shipped MP-CAT-000 through MP-CAT-005 missions.

## 6. Canonical Sprint Truth

| Sprint | Mission | Status |
|---|---|---|
| 000 | Core Foundation | closed |
| 001 | State Transition Engine | closed |
| 002 | Evidence Gate + Closeout Engine | closed |
| 003 | CI Governance + Self-Healing Validation | learned |
| 004 | V2 Alignment Guards | learned |
| 005 | Multi-Model Coding Harness MVP | closed |
| 006 | Harness Engineering Alignment | closed |
| 007 | LOGHOUSE Intelligence | closed |
| 008 | State Alignment Governance | learned |
| 009 | Repo Alignment + Mission Packet Reconciliation | active |
| 010 | GitHub Bridge + PR Governance | backlog |
| 011 | Agent Scorecard Automation | backlog |
| 012 | CAT Portable Project Adapter | backlog |

## 7. Architecture

Sprint 009 introduces a reconciliation layer:

```text
Repository Files
  -> Registry Audit
  -> Roadmap Sync Check
  -> Reconciliation Target Comparison
  -> Evidence Report
  -> State Update
```

## 8. New Rule

```text
No Reconciled Registry = No New Sprint
```

## 9. Risk Assessment

| Risk | Level | Mitigation |
|---|---|---|
| Incorrect registry state | Medium | Audit script + target state file |
| Stale roadmap | Medium | Roadmap sync checker |
| Old BEADs selected by GO resolver | Medium | Active mission reset to MP-CAT-A009-4C01 |
| Overwriting useful work | Low | Reconciliation is additive and reversible |
| Premature next sprint | Medium | Explicit gate prevents A010 before A009 pass |

## 10. Validation Strategy

Required checks:

```bash
python scripts/cat_registry_audit.py --registry missions/registry/MISSION_REGISTRY.yaml
python scripts/cat_reconcile.py --target docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml --write-report
python scripts/cat_roadmap_sync.py --check
python scripts/cat_align_check.py --strict
pytest -q
```

## 11. Rollback Strategy

All Sprint 009 changes are text-based and reversible via Git.

Rollback path:

1. Revert Sprint 009 commit.
2. Restore prior registry and roadmap.
3. Re-run CAT baseline validation.
4. Re-open reconciliation as a fresh BEAD if needed.

## 12. Definition of Done

- `MP-CAT-A009-4C01` exists and is active.
- Sprint 009 BEADs exist.
- `MISSION_REGISTRY.yaml` lists missions through `MP-CAT-A012-4C01`.
- `CAT_ROADMAP.md` matches canonical sprint truth.
- Reconciliation scripts and tests pass.
- Evidence report is generated.

## 13. Next Sprint

After successful closeout, proceed to:

```text
MP-CAT-A010-4C01: GitHub Bridge + PR Governance
```
