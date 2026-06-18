# CAT State Transitions

## Core Rule

Lifecycle status is not edited casually. Use the transition engine.

```bash
python scripts/cat_transition.py --type bead --id BEAD-CAT-001-001 --to in_progress --reason "begin implementation" --dry-run
```

Apply without `--dry-run` only after the dry-run result is accepted.

## Mission Lifecycle

```text
draft -> triaged -> approved -> dispatched -> in_progress -> validating -> reviewed -> closed -> learned
```

Blocked paths are explicit:

```text
blocked, escalated, incident, rolled_back, abandoned
```

## BEAD Lifecycle

```text
queued -> active -> in_progress -> validating -> reviewed -> completed -> archived
```

Failure paths are explicit:

```text
blocked, changes_requested, failed
```

## Evidence-Required Targets

Mission targets requiring evidence:

- validating
- reviewed
- closed
- learned
- rolled_back
- incident

BEAD targets requiring evidence:

- validating
- reviewed
- completed
- failed

## Audit Log

Applied and denied transitions write to:

```text
evidence/logs/transitions.jsonl
```

Dry-run transitions print results but do not mutate contracts or write audit events unless denied. Denied transitions always write an audit event so governance failures remain visible.
