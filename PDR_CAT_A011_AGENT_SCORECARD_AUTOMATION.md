# PDR: Agent Scorecard Automation

**PDR ID:** PDR-CAT-A011  
**Mission:** MP-CAT-A011-4C01  
**Status:** approved  
**Date:** 2026-06-18  
**Author:** Orchestrator + Human Owner  

---

## Problem

`agents/registry/AGENT_SCORECARD.yaml` is a static placeholder (v0.0.0, zeroed
counters). No automation updates it after BEADs complete or incidents occur.
Agent trust levels are meaningless without a feedback loop from actual delivery
history.

---

## Decision

Build a three-layer automation:

1. **Schema layer** — `schemas/agent_scorecard.schema.json` so the scorecard
   data structure is validated like any other contract.
2. **Scoring engine** — `scripts/cat_agent_scorecard.py` CLI for recording BEAD
   outcomes and computing trust scores.
3. **Budget tracker** — `scripts/cat_tool_budget_tracker.py` to compare
   actual tool usage against BEAD contract budgets.
4. **Closeout integration** — hook scoring engine into `cat_sprint_closeout.py`
   so every BEAD closeout automatically records a delta.

---

## Scoring Formula

| Event | Score Delta |
|-------|-------------|
| BEAD completed | +5 |
| BEAD failed | -10 |
| Incident penalty | -15 |
| Floor (severe incident) | 40 |
| Promote threshold | ≥ 85 → `trusted` |
| Demote threshold | ≤ 55 → `restricted` |

Starting score: 70 (per existing `score_policy`).

---

## Trust Levels

| Level | Score Range | Notes |
|-------|-------------|-------|
| `provisional` | < 85, > 55 | Default for new agents |
| `trusted` | ≥ 85 | Human Owner approval required to set |
| `restricted` | ≤ 55 | Human Owner approval required to set |

---

## Human Gate

All trust-level changes (`trusted` / `restricted` promotion/demotion) require
explicit `--execute` flag **and** a human-approved commit on the AGENT_SCORECARD
file. The `score-bead` subcommand records score numerics in dry-run by default.

---

## Alternatives Considered

| Option | Rejected Reason |
|--------|-----------------|
| Auto-promote on score ≥ 85 | Violates L2 autonomy constraint; trust changes need human sign-off |
| Separate JSON event log | Adds storage layer; YAML history field in scorecard is sufficient |
| Integrate with GitHub Actions | Out of scope for A011; can be added in A012+ |

---

## Risk

| Risk | Mitigation |
|------|-----------|
| Scorecard drift if closeout hook errors | Default dry-run; errors logged but don't block closeout |
| Backslash path in BEAD contract | All paths use forward slashes per PATTERN_LIBRARY anti-pattern |
| Nullable YAML fields | All `.get()` calls use `or []` / `or {}` pattern |

---

## BEADs

- BEAD-CAT-A011-4C01-01 — Schema + data model
- BEAD-CAT-A011-4C01-02 — Scoring engine CLI
- BEAD-CAT-A011-4C01-03 — Tool-budget tracker
- BEAD-CAT-A011-4C01-04 — Closeout integration + evidence

---

## Evidence Path

`evidence/scorecard/`
