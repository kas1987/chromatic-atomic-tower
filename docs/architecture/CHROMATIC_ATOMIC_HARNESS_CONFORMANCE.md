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
| **Input** — intent, repo state, backlog, constraints | ✅ | `scripts/cat_issue_intake.py` (issue → intent); `schemas/intent_envelope.schema.json` (normalized intent envelope) |

---

## 2. End-to-End GO-Mode Pipeline (7 stages)

| # | Stage | Status | Implementation |
|---|-------|--------|----------------|
| 1 | **Intent** | ✅ | `scripts/cat_issue_intake.py`; normalized envelope `schemas/intent_envelope.schema.json` |
| 2 | **Mission Pack** | ✅ | `scripts/cat_new_mission.py`, `scripts/cat_resolve_go.py` |
| 3 | **Plan & Decompose** | ✅ | `scripts/cat_new_bead.py` |
| 4 | **Execute** | ✅ | `scripts/harness_run.py` (one loop iteration) |
| 5 | **Observe & Capture** | ✅ | `scripts/cat_run_log.py`, `scripts/cat_loghouse.py`, `scripts/loghouse/` |
| 6 | **Score & Validate** | ✅ | `scripts/cat_score_confidence.py`, `scripts/cat_validate.py`, `gates/` |
| 7 | **Continue / Close** | ✅ | `scripts/cat_transition.py`, `scripts/cat_closeout.py`, `scripts/cat_sprint_closeout.py` |

**GO-mode driver — now two-tier.** `scripts/cat_go.py` is the **read-only spine**
(evaluates all 7 stages → `go_run_record`; A011 → 7/7). `scripts/cat_go_run.py`
is the **active orchestrator** (G-1a): it picks the next actionable stage and,
under `--execute`, advances it by delegating to audited scripts
(`cat_sprint_closeout.py`) — default dry-run, never mutates state directly. The
mission-close gate stays enforced but is **approved by an agent** (the
`gate_approver_agent`, default Auditor) rather than a human — see §6.

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
| **Handoff** — dispatch packet, context package, continuity | ✅ | `schemas/handoff_packet.schema.json` (structured packet: roles, context_paths, continuity, tool_budget); `state/AGENT_HANDOFF_QUEUE.md` queue |
| **Queue** — next tasks added to backlog with priority | ✅ | `missions/backlog/`, dispatch queue |
| Outputs: Final Report · Mission Package · Next Steps · Audit Log | ✅ | `scripts/cat_mission_package.py` (+ `schemas/mission_package.schema.json`) bundles the review-ready package per mission; transition/closeout JSONL = audit log |

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

**Gate approver — agent, not human.** The `human_gate_if_required` guard
(`scripts/cat_transition.py`) stays enforced, but approval is now recorded by
the configured **`gate_approver_agent`** (`gates/state/transition_rules.yaml`,
default **Auditor**) instead of a human. The Auditor is independent of the
Builder/Orchestrator that perform the work, preserving separation of duties; a
misconfigured approver (not a registered role) **fails** the gate — keeping
"No Gate = No Promotion" intact without a human in the loop. PR-governance
gates (`gates/github/`) are unchanged.

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
| **G-7** | First-class Database & Calendar/Email tool planes (schema + adapter scaffolding) | Tool layer | mission pack |

### Recently closed

- **G-1b — orchestrator automates Score & Validate** — `cat_go_run.py` now
  runs the validation gate (`cat_validate.py --all`) as a safe read-only
  `check` action when `score_validate` is the next stage; close stays a gated
  `mutate`. Remaining stages (intent…execute) are intentionally agent-driven.
- **G-1a — active GO-mode orchestrator** — `scripts/cat_go_run.py` picks the
  next actionable stage and advances it under `--execute` by
  delegating to `cat_sprint_closeout.py`; default dry-run, agent-approved gate
  gate, no direct state mutation.
- **G-2 — intent envelope schema** — `schemas/intent_envelope.schema.json`
  normalizes pipeline stage 1 (Intent), validated via `cat_validate --all`.
- **G-3 — handoff packet schema** — `schemas/handoff_packet.schema.json`
  structures the Orchestrator-layer Handoff (roles, context, continuity, budget).
- **G-4 — mission package artifact** — `scripts/cat_mission_package.py` +
  `schemas/mission_package.schema.json` produce the review-ready bundle per mission.
- **G-1 spine — GO-mode pipeline status driver** — `scripts/cat_go.py`
  evaluates all 7 stages read-only and emits a `go_run_record` (Sprint 011).
- **G-6 — control-plane docs** — `CONTROL_PLANES.md` expanded from stub to a
  full plane↔implementation reference incl. the Collect→…→Recommend flow.
- **G-5 — Scorecard parity in CI** — `scorecard_parity` check added to
  `scripts/cat_ci.py` `CHECKS`; the gate now fails if any registry role is
  untracked (Sprint 011).
- **Agent Layer parity** — AGENT_SCORECARD now tracks all 7 registry roles;
  `cat_agent_scorecard.py check-parity` enforces it (Sprint 011).
- **Scorecard correctness** — idempotent `score-bead`, archived-BEAD outcome
  derivation in closeout (Sprint 011 / PR #27).
