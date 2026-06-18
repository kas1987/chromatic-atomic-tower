# Chromatic Atomic Harness — Architecture Conformance Map

**Purpose.** This document is the authoritative cross-reference between the
*Chromatic Atomic Harness* (CAH) north-star architecture diagram and the
implemented CAT repository. It exists to make "build to this" an explicit,
auditable target rather than an aspiration — in keeping with the design
principle **Auditable by default**.

Each diagram component is marked:

- ✅ **Implemented** — present and verified in the repo.
- 🟡 **Partial** — pieces exist but are not unified, complete, or wired end-to-end.
- ❌ **Missing** — no implementation yet.

Last reconciled: 2026-06-18 (Sprint 011 / post-A011).

---

## 1. Core Stack

| Component | Status | Implementation |
|-----------|--------|----------------|
| **CAT Core** — mission registry, state machine, rules, schemas, validation | ✅ | `missions/registry/MISSION_REGISTRY.yaml`, `gates/state/transition_rules.yaml`, `schemas/` (26 schemas), `scripts/cat_validate.py`, `scripts/cat_transition.py` |
| **Mission Packs** — M1–M4 contracts | ✅ | `missions/`, `schemas/mission.schema.json` (level enum M1–M4), `scripts/cat_new_mission.py` |
| **BEADs** — atomic execution units | ✅ | `beads/`, `schemas/bead.schema.json`, `scripts/cat_new_bead.py` |
| **Agent Layer** — Orchestrator, Scout, Builder, Reviewer, Auditor, Scribe, Security | ✅ | `agents/registry/AGENT_REGISTRY.yaml` (7 roles), `agents/roles/*.md` (7 role files), `agents/registry/AGENT_SCORECARD.yaml` (7 roles, parity-enforced) |
| **Evidence Fabric** — logs, diffs, tests, metrics, artifacts, lessons | ✅ | `evidence/`, `scripts/cat_evidence.py`, `scripts/cat_generate_evidence_bundle.py` |
| **Input** — intent, repo state, backlog, constraints | 🟡 | `scripts/cat_issue_intake.py` (issue → intent). No single normalized intent envelope. |

---

## 2. End-to-End GO-Mode Pipeline (7 stages)

| # | Stage | Status | Implementation |
|---|-------|--------|----------------|
| 1 | **Intent** | 🟡 | `scripts/cat_issue_intake.py` |
| 2 | **Mission Pack** | ✅ | `scripts/cat_new_mission.py`, `scripts/cat_resolve_go.py` |
| 3 | **Plan & Decompose** | ✅ | `scripts/cat_new_bead.py` |
| 4 | **Execute** | ✅ | `scripts/harness_run.py` (one loop iteration) |
| 5 | **Observe & Capture** | ✅ | `scripts/cat_run_log.py`, `scripts/cat_loghouse.py`, `scripts/loghouse/` |
| 6 | **Score & Validate** | ✅ | `scripts/cat_score_confidence.py`, `scripts/cat_validate.py`, `gates/` |
| 7 | **Continue / Close** | ✅ | `scripts/cat_transition.py`, `scripts/cat_closeout.py`, `scripts/cat_sprint_closeout.py` |

**Gap (G-1) — spine landed, orchestration pending.** `scripts/cat_go.py` now
provides the **read-only GO-mode spine**: for a mission it evaluates all 7
stages and emits one `go_run_record` (see `python scripts/cat_go.py --mission
MP-CAT-A011-4C01` → 7/7 satisfied). What remains is the *active* orchestrator
that advances a mission stage-by-stage (mutating state with confidence-gate +
human-gate checks) rather than only reporting status. Tracked as **G-1a**.

---

## 3. Atomic Control Planes

| Plane | Status | Implementation |
|-------|--------|----------------|
| **Mission Plane** — registry, M1–M4, status+ownership, acceptance criteria | ✅ | `missions/registry/`, `docs/architecture/CONTROL_PLANES.md` |
| **Execution Plane** — BEAD queue, allowed/forbidden files, tool budgets, stop conditions | ✅ | `beads/`, `schemas/dispatch_queue_item.schema.json`, `scripts/cat_tool_budget_tracker.py`, `scripts/cat_changed_files_guard.py` |
| **Evidence Plane** — test results, diff bundles, validation reports, audit trail | ✅ | `evidence/`, `schemas/evidence_bundle.schema.json` |
| **Learning Plane** — decision logs, incident learnings, agent scorecards, pattern library | ✅ | `learnings/DECISION_LOG.md`, `learnings/INCIDENT_LOG.md`, `learnings/PATTERN_LIBRARY.md`, `learnings/ECHO_LOG.md`, `agents/registry/AGENT_SCORECARD.yaml` |
| **Flow** — Collect → Normalize → Correlate → Score → Validate → Learn → Recommend | ✅ | `scripts/loghouse/` (`normalize.py`, `correlate.py`, `rules.py`), `scripts/cat_loghouse.py` `run_pipeline()` |

---

## 4. Agent Lead / Orchestrator Layer

| Capability | Status | Implementation |
|------------|--------|----------------|
| **Synthesize** — merge mission state + evidence + repo context | 🟡 | `scripts/cat_status.py`, `scripts/cat_reconcile.py` |
| **Evaluate** — confidence/risk/quality/cost scores | ✅ | `scripts/cat_score_confidence.py` |
| **Recommend** — best next BEAD, alternate path, rollback | 🟡 | `scripts/cat_resolve_go.py` (GO decision); rollback/alternate-path surfacing partial |
| **Report** — executive summary, findings, evidence bundle | ✅ | `scripts/cat_generate_evidence_bundle.py`, `evidence/reports/` |
| **Handoff** — dispatch packet, context package, continuity | 🟡 | `state/AGENT_HANDOFF_QUEUE.md` (manual queue); no structured handoff packet schema |
| **Queue** — next tasks added to backlog with priority | ✅ | `missions/backlog/`, dispatch queue |
| Outputs: Final Report · Mission Package · Next Steps · Audit Log | 🟡 | Evidence reports + transition/closeout logs cover most; no single bundled "mission package" artifact per GO run |

---

## 5. Confidence Gate

✅ **Implemented** — `scripts/cat_score_confidence.py` band logic matches the diagram exactly:

| Score | Diagram | Code (`band()`) |
|-------|---------|-----------------|
| 90–100 | Auto-Proceed | `auto_proceed` |
| 70–89 | Proceed | `proceed_with_review` |
| 50–69 | Caution / Self-Heal | `self_heal` |
| 0–49 | Escalate / Replan | `escalate_or_block` |

Self-heal path: `scripts/cat_self_heal.py`.

---

## 6. Governance Rules

✅ All five enforced and encoded in `docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml` and gate scripts:

- No Mission = No Work
- No BEAD = No Dispatch
- No Evidence = No Closeout
- No Gate = No Promotion
- No Registry Entry = No Commit
- *(+ No Reconciled Registry = No New Sprint — CAT extension)*

---

## 7. Design Principles

✅ Reflected throughout: Small but strict · Bounded autonomy (`autonomy_level` per
role/BEAD) · Evidence over assumption (deferred guards require evidence paths) ·
Deterministic outcomes (state machine) · Reusable contracts (mission/BEAD schemas)
· Auditable by default (transition + closeout JSONL logs, this document).

---

## 8. Tool + Context Layer

| Tool | Status | Implementation |
|------|--------|----------------|
| Git / GitHub | ✅ | `scripts/cat_git_bridge.py`, `.github/workflows/` |
| Filesystem | ✅ | filesystem-native by design |
| Terminal / Shell | ✅ | script execution layer |
| Web / Search | ✅ | harness tool layer |
| LLM / Models — **any model, any provider** | ✅ | `docs/architecture/LLM_MODEL_ROUTING.md`, `schemas/model_routing_policy.schema.json`, MP-CAT-005 multi-model harness |
| Database | 🟡 | SQLite via loghouse / codegraph; not a first-class plane |
| Calendar / Email | ❌ | not implemented (out of current scope) |
| Custom Tools / 3rd-Party APIs | 🟡 | extensible via harness tool registry |

---

## 9. Gap Backlog (build-to-this)

Ordered by leverage. Each becomes a mission or BEAD when scheduled.

| ID | Gap | Plane | Proposed vehicle |
|----|-----|-------|------------------|
| **G-1a** | Active GO-mode orchestrator that *advances* a mission stage-by-stage (state mutation + confidence/human gates), beyond the read-only spine | Pipeline | New mission: *GO-Mode Orchestrator* |
| **G-2** | Intent stage lacks a normalized intent envelope schema | Input | BEAD under G-1 |
| **G-3** | Handoff has no structured packet schema (manual `.md` queue) | Orchestrator | `schemas/handoff_packet.schema.json` + wiring |
| **G-4** | No single bundled "Mission Package" artifact per GO run | Orchestrator | BEAD under G-1 |
| **G-6** | Control-plane docs (`CONTROL_PLANES.md`) are stubs vs. this map | Docs | Expand to reference implementations |

### Recently closed

- **G-1 spine — GO-mode pipeline status driver** — `scripts/cat_go.py`
  evaluates all 7 stages read-only and emits a `go_run_record` (Sprint 011).
- **G-5 — Scorecard parity in CI** — `scorecard_parity` check added to
  `scripts/cat_ci.py` `CHECKS`; the gate now fails if any registry role is
  untracked (Sprint 011).
- **Agent Layer parity** — AGENT_SCORECARD now tracks all 7 registry roles;
  `cat_agent_scorecard.py check-parity` enforces it (Sprint 011).
- **Scorecard correctness** — idempotent `score-bead`, archived-BEAD outcome
  derivation in closeout (Sprint 011 / PR #27).
