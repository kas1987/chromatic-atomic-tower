# Harness v2 to CAT Alignment Matrix

## Purpose

This matrix records which proven `chromatic-harness-v2` operating practices CAT should adopt, defer, or reject. The goal is compact Tower-native governance, not wholesale migration of v2 runtime sprawl.

Reference repo reviewed read-only: `C:/Users/kas41/chromatic-harness-v2`.

## Summary

| v2 Practice | v2 Evidence | CAT Decision | CAT Owner Plane | Future BEAD | Rationale |
|---|---|---|---|---|---|
| Pre-session unified guard | `AGENT_OPERATIONS.md`, `scripts/session_unified_guard.py`, `07_LOGS_AND_AUDIT/unified_guard/latest.json` | Adopt | State Plane / Automation Plane | BEAD-CAT-004-004 | CAT needs one command that checks GO readiness, state freshness, and hygiene before work starts. |
| Decision record before mutation | `docs/playbooks/GO_MODE_PLAYBOOK.md`, `00_SOURCE_OF_TRUTH/HARNESS_EXECUTION_FLOW.md` | Adopt | Mission Plane / Evidence Plane | BEAD-CAT-004-004 | CAT already has mission/BEAD dispatch; durable GO decision records will make it recoverable and auditable. |
| State freshness and drift checks | `07_LOGS_AND_AUDIT/drift/latest.json` | Adopt | State Plane | BEAD-CAT-004-002 | CAT exposed stale Tower state after MP-CAT-003 learned while `TOWER_STATE.yaml` still described Sprint 003 active. |
| Branch governance audit | `config/ci/branch_governance.yaml`, `07_LOGS_AND_AUDIT/ci/branch_governance_latest.md` | Adopt, dry-run only | Gate Plane / Automation Plane | BEAD-CAT-004-003 | Branch limits and protected-branch awareness help PR hygiene, but CAT should only report by default. |
| Root artifact hygiene | `07_LOGS_AND_AUDIT/root_artifacts/latest_root_artifact_hygiene.json` | Adopt, dry-run only | Gate Plane / Automation Plane | BEAD-CAT-004-003 | CAT should flag disposable root artifacts without deleting or moving anything automatically. |
| Activity log and dual backlog lanes | `docs/governance/ACTIVITY_LOG_AND_DUAL_BACKLOG.md` | Defer | Mission Plane / Review Plane | Future MP-CAT-005 | Useful, but CAT should first stabilize Tower guard and state freshness before adding lane semantics. |
| Budget forecasting and provider burn | `config/routing/budget-policy.yaml`, `07_LOGS_AND_AUDIT/budget/forecast_latest.json` | Defer | Agent Plane / Evidence Plane | Future MP-CAT-005 | CAT has model routing, but runtime cost telemetry needs a separate budget evidence mission. |
| MCP/token context hygiene | `AGENT_OPERATIONS.md`, `config/pre_session/mcp.profile.yaml` | Defer | Agent Plane / Automation Plane | Future MP-CAT-005 | Valuable for IDE contexts, but not required for the first Tower guard MVP. |
| Visual control plane | `README.md`, `visual_node_registry.json`, `05_FRONTEND_CONSOLE/` | Reject for Sprint 004 | Knowledge Plane | None | CAT should remain contract-first and compact before adding UI visualization. |
| Automatic git merge autonomy | `docs/workflows/GIT_CONFIDENCE_PIPELINE.md` | Reject for CAT core | Governance Plane | None | CAT hard limits require human merge approval; autonomous merge is outside current Tower policy. |
| Bulk v2 folder topology | numbered folders such as `00_SOURCE_OF_TRUTH`, `07_LOGS_AND_AUDIT`, `12_HANDOFFS` | Reject | Tree Governance | None | CAT already has a cleaner plane map in `CAT_MANIFEST.md` and `CHROMATIC_TREES.md`. |

## Adopted Pattern Details

### 1. Tower Guard

CAT should add a `scripts/cat_tower_guard.py` command that combines smaller checks and writes durable evidence. It should answer:

- Is `MISSION_REGISTRY.yaml` consistent with mission files?
- Is `state/TOWER_STATE.yaml` pointing at the selected mission and BEAD?
- Is GO ready or blocked?
- Are branch and root hygiene checks clean?

The guard must report. It must not repair, prune, merge, delete, or mutate state by default.

### 2. State Freshness

CAT should treat stale Tower state as a first-class governance failure. A stale state exists when:

- `active_mission_id` points to a terminal mission.
- `active_bead_id` points to an archived BEAD.
- registry `active_mission_id` and Tower `active_mission_id` disagree.
- mission `current_bead_id` and Tower `active_bead_id` disagree without a terminal explanation.

### 3. Hygiene Checks

Branch and root hygiene should be dry-run checks only:

- protected branches are listed and never mutated;
- stale branches are reported but not deleted;
- disposable root artifacts are reported but not removed;
- new top-level entries require manifest or mission authorization.

## Deferred Patterns

Lane-aware backlog and budget telemetry are important, but they should not be folded into Sprint 004. They involve policy choices about how CAT maps human/review/agent lanes and how cost events become evidence. Those deserve a focused mission after Tower guard basics pass.

## Rejected Patterns

CAT should not copy v2's broad directory topology, visual console, or autonomous merge posture. CAT's advantage is a compact mission -> BEAD -> evidence kernel with explicit human merge gates.

## Next BEAD Mapping

| BEAD | Alignment Work |
|---|---|
| BEAD-CAT-004-002 | Implement state freshness checks. |
| BEAD-CAT-004-003 | Implement dry-run branch/root hygiene checks. |
| BEAD-CAT-004-004 | Combine checks into unified Tower guard report and operator docs. |
