# Self-Review: BEAD-CAT-001-001 — Transition rules & state machine

- Mission: MP-CAT-001 — Implement CAT State Transition Engine
- BEAD: BEAD-CAT-001-001 — Define transition rules and state machine diagram
- Agent role: Architect
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Defined the canonical CAT state machine for both mission and BEAD lifecycles as a
machine-checkable rules document, rendered it as Mermaid diagrams, and superseded
the Sprint 000 adjacency-only placeholder. The rules are the single source of truth
the transition CLI (BEAD-CAT-001-002) will load and enforce.

## Files changed

- `gates/state/transition_rules.yaml` — **new** canonical rules (32 mission arcs, 20 BEAD arcs; each with `guard` + `reversible`, plus a `guards` vocabulary and terminal-state lists).
- `docs/architecture/STATE_MACHINE.md` — rewritten with Mermaid `stateDiagram-v2` for both lifecycles, a legend, and an enforcement note.
- `gates/state/STATE_TRANSITION_RULES.yaml` — **removed** (superseded; was `version 0.0.0`, adjacency-only, no guards/reversibility; confirmed no code references it).

## Validation

Programmatic check of the rules against the authoritative schema enums
(`schemas/mission.schema.json`, `schemas/bead.schema.json`):

```text
mission: 32 arcs, 14/14 states covered
bead:    20 arcs, 10/10 states covered
RESULT: PASS
```

- Every `from`/`to` is a valid enum value; no `(from,to)` duplicates; every `guard` is defined in the `guards` block.
- `python scripts/cat_validate.py --all` → PASS (no contract files altered).

## Definition of Done

- [x] `gates/state/transition_rules.yaml` enumerates every valid `(from,to)` pair for mission and BEAD states.
- [x] Each rule includes a guard condition and a reversibility flag.
- [x] `docs/architecture/STATE_MACHINE.md` contains Mermaid diagrams rendered from the rules.
- [x] This self-review report recorded.

## Design decisions & assumptions (flagged for Human Owner review)

1. **Guards are named, not yet implemented.** This BEAD defines the guard *vocabulary*
   (`human_gate_if_required`, `review_gate_pass`, `evidence_present`, …); evaluating
   them is BEAD-CAT-001-002's job. The names map to existing gates/checklists.
2. **`reversible` marks deliberate loop-backs** (rework, unblock, retry, re-triage),
   not forward progress. Used later to decide which transitions are safe to auto-apply
   vs require confirmation.
3. **Terminal states:** missions — `abandoned`, `learned` (and `closed` except
   `closed→learned`); BEADs — `archived` (and `completed` except `completed→archived`).
4. **`reviewed→in_progress` (mission) and `changes_requested→in_progress/active`
   (BEAD)** added as rework arcs — not in the old placeholder, but required so review
   rejection has a path back to work without abandoning the unit.
5. **`escalated` / `incident` / `rolled_back`** wired into the mission graph (the old
   placeholder left them partly dangling): `in_progress→escalated→{approved,blocked,
   abandoned}` and `in_progress/validating→incident→{rolled_back,blocked,abandoned}`.

**Open question for the owner:** should `approved→dispatched` and `queued→active`
require the GO resolver specifically (vs any operator), and should `reviewed→closed`
hard-require `human_gate` for high-risk missions? Encoded as guards now; enforcement
policy is BEAD-CAT-001-002.

## Handoff

Next: **BEAD-CAT-001-002** — `scripts/cat_transition.py` loads `transition_rules.yaml`,
rejects unlisted arcs, evaluates guards, and logs to `evidence/logs/transitions.jsonl`.
