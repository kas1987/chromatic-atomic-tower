# Self-Review: BEAD-CAT-001-003 — snapshot/rollback logic

- Mission: MP-CAT-001 — Implement CAT State Transition Engine
- BEAD: BEAD-CAT-001-003 — Implement atomic registry mutation and snapshot/rollback logic
- Agent role: Builder
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Extended `scripts/cat_transition.py` with pre-transition snapshot creation and
`--rollback <snapshot_id>` mode. Every `--execute` invocation now captures the
mutable state files before any mutation; `--rollback` atomically restores them
and emits a rollback evidence record.

## Files changed

- `scripts/cat_transition.py` — extended with snapshot and rollback logic.
- `evidence/transitions/transition_log.jsonl` — **new** (snapshot_created and
  rollback_applied events; created on first invocation).
- `evidence/rollbacks/<snapshot_id>.jsonl` — **new** (per-rollback records;
  created on first rollback invocation).
- `evidence/snapshots/<snapshot_id>/` — **new** per-execute snapshot directories.

## Definition of Done

- [x] `--execute` creates a timestamped snapshot before mutating any file.
- [x] `--rollback <snapshot_id>` restores all snapshotted files atomically and
  writes a rollback evidence record to `evidence/rollbacks/`.
- [x] All mutations (execute and rollback) remain atomic via temp-file + rename.
- [x] Snapshot metadata is recorded in `evidence/transitions/transition_log.jsonl`.

## Validation

```text
# Execute creates snapshot + mutates
$ python scripts/cat_transition.py --execute --mission MP-CAT-001 \
    --from approved --to blocked --reason "snapshot test"
[execute] snapshot   : snap_20260617T201512Z  (evidence\snapshots\snap_20260617T201512Z)
[execute] MP-CAT-001.status = 'blocked'  (missions\registry\MISSION_REGISTRY.yaml updated)
[execute] rollback via: cat_transition.py --rollback snap_20260617T201512Z
exit: 0  ✓

# Rollback restores files
$ python scripts/cat_transition.py --rollback snap_20260617T201512Z \
    --reason "rollback smoke test"
  restored: missions\registry\MISSION_REGISTRY.yaml
  restored: state\TOWER_STATE.yaml
  evidence: evidence\rollbacks\snap_20260617T201512Z.jsonl
exit: 0  ✓
$ grep "status:" missions/registry/MISSION_REGISTRY.yaml
  status: closed
  status: approved   # ← MP-CAT-001 restored ✓
  status: approved

# Bad snapshot ID
$ python scripts/cat_transition.py --rollback snap_doesnotexist
ERROR: snapshot 'snap_doesnotexist' not found at evidence\snapshots\snap_doesnotexist
exit: 1  ✓

# transition_log.jsonl shows both events
$ cat evidence/transitions/transition_log.jsonl
{"event": "snapshot_created", "snapshot_id": "snap_20260617T201512Z", ...}
{"event": "rollback_applied", "snapshot_id": "snap_20260617T201512Z", ...}
✓

RESULT: PASS
```

## Design decisions

1. **Snapshot ID format**: `snap_YYYYMMDDTHHMMSSZ` (UTC, filesystem-safe, sortable).
   One snapshot per second; calling `--execute` twice within one second overwrites
   the snapshot directory. BEAD-CAT-001-004's pytest suite should mock or parameterise
   the timestamp to keep snapshot IDs deterministic in tests.
2. **Files snapshotted**: `MISSION_REGISTRY.yaml` always; the BEAD YAML for BEAD
   transitions; all `*.yaml` files under a top-level `state/` directory if it exists.
   (`state/TOWER_STATE.yaml` was found in this run.)
3. **Rollback updates `last_updated`**: restored YAML files get a fresh timestamp so
   downstream readers can detect the restore event rather than seeing a stale timestamp.
4. **Two evidence streams**: `evidence/logs/transitions.jsonl` records every transition
   invocation (existing from BEAD-CAT-001-002); `evidence/transitions/transition_log.jsonl`
   records snapshot and rollback lifecycle events (new in this BEAD). Kept separate so
   the transition log is a clean structural audit trail independent of transition outcomes.

## Handoff

Next: **BEAD-CAT-001-004** — pytest suite. Snapshot IDs are time-based; tests should
mock `_snapshot_id()` or pass `--snapshot-id` to get deterministic IDs in assertions.
