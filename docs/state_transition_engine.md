# CAT State Transition Engine

## Overview

`scripts/cat_transition.py` is the sole authority for mutating mission and BEAD status
in the Chromatic Atomic Tower. It enforces valid lifecycle arcs, evaluates guards, creates
pre-mutation snapshots, updates the registry and tower state, and appends audit events.

No code or agent may hand-edit the `status` field on a mission or BEAD contract.
All state changes flow through `cat_transition.py`.

## Rules Files

The engine searches for transition rules in this order:

1. `state/transition_rules.yaml` — governance-layer alias (added by BEAD-CAT-A014-4C01-01)
2. `gates/state/transition_rules.yaml` — canonical arc-list rules
3. `gates/state/STATE_TRANSITION_RULES.yaml` — legacy fallback

Only the first file found is used. Edit `gates/state/transition_rules.yaml` to change rules.
`state/transition_rules.yaml` is an alias that documents the lifecycle summary.

## Schema

Individual transition arcs follow `schemas/state_transition.schema.json`:

```json
{
  "from": "in_progress",
  "to": "validating",
  "guard": "evidence_present",
  "reversible": false
}
```

## BEAD Lifecycle

```
queued → active → in_progress → validating → reviewed → completed → archived
                      ↓                ↓
                   blocked          failed
                      ↓
                  escalated
```

Terminal state: `archived`

Evidence required for: `in_progress → validating` (guard: `evidence_present`)

## Mission Lifecycle

```
draft → triaged → approved → dispatched → in_progress → validating → reviewed → closed → learned
                                                  ↓
                                              blocked → escalated
                                                  ↓
                                             abandoned
```

Terminal states: `abandoned`, `learned`

## Usage

### Dry-run (check without mutating)

```bash
python scripts/cat_transition.py --dry-run --bead BEAD-CAT-A014-4C01-01 --to active \
  --reason "Kickoff BEAD-01" --actor "Builder"
```

### Execute a transition

```bash
python scripts/cat_transition.py --execute --bead BEAD-CAT-A014-4C01-01 --to active \
  --reason "Kickoff BEAD-01" --actor "Builder"
```

### Rollback from a snapshot

```bash
python scripts/cat_transition.py --rollback snap_20260618T123456_000000Z
```

### JSON output

Add `--json` to either `--dry-run` or `--execute` to get machine-readable output:

```bash
python scripts/cat_transition.py --dry-run --bead BEAD-CAT-A014-4C01-01 --to active \
  --reason "test" --actor "pytest" --json
```

## Guards

| Guard | Description |
|---|---|
| `none` | Always permitted |
| `active_bead_present` | Mission has a non-null `current_bead_id` whose BEAD exists on disk |
| `evidence_present` | Required evidence artifacts exist on disk |
| `validation_passed` | All required validations returned success |
| `review_gate_pass` | Review gate recorded an approve decision |
| `human_gate_if_required` | If `human_gate.required`, approval recorded by `gate_approver_agent` |
| `closeout_complete` | Closeout report + learning log recorded |

## Audit Log

Every transition (allowed or denied, dry-run or execute) is appended to:

```
evidence/logs/transitions.jsonl
```

Each line is a JSON object with fields: `timestamp`, `target_type`, `target_id`,
`from_status`, `to_status`, `allowed`, `dry_run`, `reason`, `evidence`, `actor`,
`message`, `contract_path`, `guard`, `guard_ok`, `guard_message`.

## Snapshots

Before every applied transition, a snapshot is created at:

```
evidence/snapshots/snap_<YYYYMMDDTHHMMSS_ffffff>Z/
```

The snapshot contains copies of the registry, tower state, and the contract being
mutated. Use `--rollback <snapshot_id>` to restore.
