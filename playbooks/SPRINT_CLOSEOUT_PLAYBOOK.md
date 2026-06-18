# Sprint Closeout Playbook

Close a mission when all BEADs are terminal but the mission remains in a working status.

## When to use

- `cat_align_check.py` reports `MISSION_BEADS_COMPLETE_MISSION_OPEN`
- All BEADs for the mission are `completed`, `failed`, or `archived`
- Mission status is still `approved`, `dispatched`, `in_progress`, etc.

## Procedure

1. Verify all BEADs terminal:

```bash
python scripts/cat_status.py
```

2. Dry-run closeout:

```bash
python scripts/cat_sprint_closeout.py --mission MP-CAT-XXX --dry-run
```

3. Execute closeout:

```bash
python scripts/cat_sprint_closeout.py --mission MP-CAT-XXX --execute \
  --evidence evidence/reports/sprint_closeout_MP-CAT-XXX.md
```

4. Confirm alignment:

```bash
python scripts/cat_align_check.py --strict
```

## Expected post-closeout state

- Mission contract: `status: closed` (moved to `missions/archived/`)
- Registry: mission entry `status: closed`, `current_bead_id: ''`
- Tower: `status: sprint_idle`, `active_mission_id: ''`, `active_bead_id: ''`
- `SPRINT_STATE.md` and `AGENT_HANDOFF_QUEUE.md` auto-regenerated

## Post-sprint DRIFT (expected vs bug)

Tower guard FAIL immediately after BEAD archival with pointers still set is **expected** until closeout runs. After closeout, alignment must PASS.

## MP-CAT-005 example

Sprint 005 (Multi-Model Harness MVP) was closed with evidence at `evidence/reports/sprint_closeout_mp_cat_005.md`. Superseded backlog collision file `MP-CAT-002_MULTI_MODEL_HARNESS.yaml` was removed.
