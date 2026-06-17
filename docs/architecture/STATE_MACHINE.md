# CAT State Machine

CAT uses explicit lifecycle state machines for missions and BEADs. The source of truth is `gates/state/STATE_TRANSITION_RULES.yaml`.

## Mission Path

```text
draft -> triaged -> approved -> dispatched -> in_progress -> validating -> reviewed -> closed -> learned
```

## BEAD Path

```text
queued -> active -> in_progress -> validating -> reviewed -> completed -> archived
```

## Error Paths

Mission error paths:

```text
blocked, escalated, incident, rolled_back, abandoned
```

BEAD error paths:

```text
blocked, changes_requested, failed
```

## Terminal Protection

Terminal states do not reopen by default. A future sprint may add human-gated override logic, but Sprint 001 intentionally keeps terminal reopening blocked.

## Evidence Rule

A status that claims validation, review, completion, failure, incident, rollback, or learning must carry evidence. The transition engine enforces this rule.
