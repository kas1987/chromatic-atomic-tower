# CAT State Machine

## Mission lifecycle

```text
DRAFT -> TRIAGED -> APPROVED -> DISPATCHED -> IN_PROGRESS -> VALIDATING -> REVIEWED -> CLOSED -> LEARNED
```

## BEAD lifecycle

```text
QUEUED -> ACTIVE -> IN_PROGRESS -> VALIDATING -> REVIEWED -> COMPLETED -> ARCHIVED
```

## Sprint 000 limitation

Sprint 000 provides the state model and rule file. Sprint 001 should enforce transitions with `scripts/cat_transition.py`.
