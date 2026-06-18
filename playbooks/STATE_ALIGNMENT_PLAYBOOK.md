# State Alignment Playbook

Operator procedures for mission/BEAD state alignment (MP-CAT-A008-4C01).

## Pre-GO checklist

```bash
python scripts/cat_align_check.py --strict
python scripts/cat_tower_guard.py
```

If either fails, do not say GO until drift is resolved.

## Drift remediation by code

| Code | Fix |
|------|-----|
| `MISSION_ID_MISMATCH` | Reconcile `TOWER_STATE.active_mission_id` and registry via `cat_transition.py` |
| `BEAD_ID_MISMATCH` | Normalize pointers to `''` in tower and registry |
| `REGISTRY_CONTRACT_STATUS_MISMATCH` | Run transition on mission contract — never hand-edit status |
| `BEAD_NOT_ACTIVE` | Transition BEAD `queued → active` before GO |
| `BEAD_TERMINAL_POINTER` | Clear `current_bead_id` and `active_bead_id` after closeout |
| `TERMINAL_MISSION_ACTIVE` | Run `cat_sprint_closeout.py` or set tower to `sprint_idle` |
| `MISSION_BEADS_COMPLETE_MISSION_OPEN` | `python scripts/cat_sprint_closeout.py --mission MP-CAT-XXX --execute` |
| `MISSION_ID_COLLISION` | Remove duplicate contract file; assign new ID at backlog creation |

## Mission ID assignment

Before creating a backlog mission:

```bash
python scripts/cat_mission_id_check.py --suggest-id
python scripts/cat_new_mission.py --template M4_ATOMIC --id MP-CAT-A009-4C01 --title "..."
```

`cat_new_mission.py` rejects duplicate IDs automatically.

## Multi-agent collision patterns

- Watch file mtimes before branch switches in shared sessions
- WIP-commit before handoff when another agent may write
- Verify `git branch --show-current` at session start (do not trust stale session metadata)

## References

- [STATE_ALIGNMENT.md](../docs/architecture/STATE_ALIGNMENT.md)
- [SPRINT_CLOSEOUT_PLAYBOOK.md](SPRINT_CLOSEOUT_PLAYBOOK.md)
