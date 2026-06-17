# Self-Review: BEAD-CAT-001-002 — scripts/cat_transition.py

- Mission: MP-CAT-001 — Implement CAT State Transition Engine
- BEAD: BEAD-CAT-001-002 — Implement scripts/cat_transition.py with dry-run and execute modes
- Agent role: Builder
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Implemented `scripts/cat_transition.py`, the CAT state-machine transition engine.
The script loads the canonical rules from `gates/state/transition_rules.yaml`,
validates the requested `(entity, from, to)` arc, evaluates the named guard, and
in execute mode atomically mutates the target file (MISSION_REGISTRY.yaml for
missions, the BEAD's own YAML for BEADs). Every invocation appends a structured
record to `evidence/logs/transitions.jsonl`.

## Files changed

- `scripts/cat_transition.py` — **new** transition engine (dry-run + execute modes,
  guard evaluation, atomic writes, evidence logging).
- `evidence/logs/transitions.jsonl` — **new** (created on first invocation; contains
  smoke-test entries from validation below).

## Definition of Done

- [x] `scripts/cat_transition.py` exists and is importable.
- [x] `--dry-run` prints the predicted diff without mutating any file.
- [x] `--execute` validates the transition and mutates the target YAML atomically
  (write-to-temp + `Path.replace()`).
- [x] Invalid transitions (`(from,to)` not in rules) exit 1 with a descriptive error.
- [x] Every invocation writes a structured record to `evidence/logs/transitions.jsonl`.

## Validation

```text
# Valid dry-run — mission
$ python scripts/cat_transition.py --dry-run --mission MP-CAT-001 \
    --from approved --to dispatched --reason "smoke test"
transition : mission MP-CAT-001  approved ->dispatched
  rule     : reversible=False
  guard    : active_bead_present  -> PASS (current_bead_id=BEAD-CAT-001-001)
[dry-run] would set MP-CAT-001.status  'approved' ->'dispatched'
exit: 0  ✓

# Invalid arc
$ python scripts/cat_transition.py --dry-run --mission MP-CAT-001 \
    --from approved --to learned
ERROR: mission transition 'approved' ->'learned' is not defined in transition_rules.yaml
exit: 1  ✓

# Current-state mismatch
$ python scripts/cat_transition.py --dry-run --mission MP-CAT-001 \
    --from dispatched --to in_progress
ERROR: MP-CAT-001 is currently 'approved', not 'dispatched'
exit: 1  ✓

# Valid dry-run — BEAD
$ python scripts/cat_transition.py --dry-run --bead BEAD-CAT-001-002 \
    --from queued --to active --reason "bead smoke test"
transition : bead BEAD-CAT-001-002  queued ->active
  rule     : reversible=False
  guard    : none  -> PASS (no precondition)
exit: 0  ✓

# Execute — mission (blocked then restored)
$ python scripts/cat_transition.py --execute --mission MP-CAT-001 \
    --from approved --to blocked --reason "execute smoke test"
[execute] MP-CAT-001.status = 'blocked'  (registry updated)  exit: 0  ✓

$ python scripts/cat_transition.py --execute --mission MP-CAT-001 \
    --from blocked --to approved --reason "restore after smoke test"
  guard    : human_gate_if_required  -> PASS (approver='Human Owner')
[execute] MP-CAT-001.status = 'approved'  exit: 0  ✓

RESULT: PASS
```

## Design decisions

1. **Atomic writes** use `tempfile.NamedTemporaryFile` in the target directory then
   `Path.replace()` — atomic on POSIX; best-effort on Windows (NTFS rename is atomic
   for same-volume moves).
2. **Guard evaluation scope**: `none`, `active_bead_present`, and
   `human_gate_if_required` are fully implemented. The remaining six guards
   (`evidence_present`, `validation_passed`, `review_gate_pass`, `escalation_ack`,
   `closeout_complete`, `rollback_plan_present`) are skipped with a warning — they
   require filesystem/gate artefact checks deferred to BEAD-CAT-001-003.
3. **BEAD vs mission targets**: missions update MISSION_REGISTRY.yaml; BEADs update
   their own YAML file (found by globbing `beads/**/{bead_id}.yaml`). This keeps the
   registry as the single source of truth for mission state while keeping BEAD YAML
   files as the source of truth for BEAD state.
4. **Evidence log** lives at `evidence/logs/transitions.jsonl` (one JSON object per
   line). Every invocation appends regardless of outcome (dry-run, applied, rejected,
   error) so the log is a complete audit trail.

## Handoff

Next: **BEAD-CAT-001-003** — implement the remaining guard evaluators
(`evidence_present`, `review_gate_pass`, etc.) and snapshot/rollback logic.
