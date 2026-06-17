# CAT State Machine

Canonical, machine-checkable transition rules live in
[`gates/state/transition_rules.yaml`](../../gates/state/transition_rules.yaml).
This document is the human-readable rendering of those rules (BEAD-CAT-001-001).
If the two disagree, the YAML wins and this diagram must be regenerated.

**Legend:** solid arc = forward lifecycle progress; arcs labelled `[rework]`,
`[unblock]`, `[retry]`, or `[re-triage]` are reversible loop-backs. Guard names
(e.g. `human_gate_if_required`, `review_gate_pass`) are defined in the `guards` block of the YAML.

## Mission lifecycle

States: `draft triaged approved dispatched in_progress validating reviewed closed
blocked escalated rolled_back abandoned incident learned`.
Terminal: `abandoned`, `learned` (`closed` is non-terminal; its only forward arc is `closed → learned`).

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> triaged
    draft --> abandoned
    triaged --> approved: human_gate_if_required
    triaged --> blocked
    approved --> dispatched: active_bead_present
    approved --> blocked
    dispatched --> in_progress
    dispatched --> blocked
    in_progress --> validating: evidence_present
    in_progress --> blocked
    in_progress --> escalated
    in_progress --> incident
    validating --> reviewed: validation_passed
    validating --> in_progress: rework
    validating --> blocked
    validating --> incident
    reviewed --> closed: review_gate_pass
    reviewed --> in_progress: rework
    reviewed --> blocked
    closed --> learned: closeout_complete
    blocked --> triaged: re-triage
    blocked --> approved: human_gate_if_required
    blocked --> escalated
    blocked --> abandoned
    escalated --> approved: escalation_ack
    escalated --> blocked
    escalated --> abandoned: escalation_ack
    incident --> rolled_back: rollback_plan_present
    incident --> blocked
    incident --> abandoned
    rolled_back --> triaged
    rolled_back --> abandoned
    abandoned --> [*]
    learned --> [*]
```

## BEAD lifecycle

States: `queued active in_progress validating reviewed completed blocked failed
changes_requested archived`. Terminal: `archived` (`completed` is non-terminal; its only forward arc is `completed → archived`).

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> active
    queued --> blocked
    active --> in_progress
    active --> blocked
    in_progress --> validating: evidence_present
    in_progress --> failed
    in_progress --> blocked
    validating --> reviewed: validation_passed
    validating --> changes_requested
    validating --> failed
    reviewed --> completed: review_gate_pass
    reviewed --> changes_requested
    changes_requested --> in_progress: rework
    changes_requested --> active: rework
    completed --> archived: closeout_complete
    failed --> queued: retry
    failed --> archived
    blocked --> active: unblock
    blocked --> queued: unblock
    blocked --> failed
    archived --> [*]
```

## Enforcement

`scripts/cat_transition.py` (BEAD-CAT-001-002) loads `transition_rules.yaml`,
rejects any unlisted `(from, to)` pair, evaluates the named guard, and records the
transition in `evidence/logs/transitions.jsonl`. This replaces the manual operator
transitions used to close Sprint 000.
