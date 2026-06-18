# State Alignment Invariants

Canonical rules enforced by `scripts/cat_align_check.py` and blocking CI.

## Surfaces

| Surface | Path | Authority |
|---------|------|-----------|
| Tower | `state/TOWER_STATE.yaml` | Operator view: sprint, active mission/bead |
| Registry | `missions/registry/MISSION_REGISTRY.yaml` | Mission index and pointers |
| Contracts | `missions/**/*.yaml`, `beads/**/*.yaml` | Per-unit status and scope |

All mutations must go through `scripts/cat_transition.py` or operator scripts (`cat_sprint_closeout.py`). Manual status edits bypass guards and cause drift.

## Invariants

1. **MISSION_ID_MATCH** — `TOWER_STATE.active_mission_id == MISSION_REGISTRY.active_mission_id` (empty string and null normalized).
2. **BEAD_ID_MATCH** — `TOWER_STATE.active_bead_id == registry.current_bead_id` for the active mission entry.
3. **REGISTRY_CONTRACT_STATUS** — Registry `missions[].status` equals mission contract file `status` for `active_mission_id`.
4. **BEAD_ACTIVE** — If `current_bead_id` is set, the BEAD exists and `status == "active"`. Terminal or queued BEADs at the pointer are drift.
5. **TERMINAL_MISSION** — `active_mission_id` must not point to a terminal mission (`closed`, `learned`, `abandoned`) unless tower `status` is `sprint_idle` or `post_sprint_idle`.
6. **MISSION_BEADS_COMPLETE** — If all BEADs for the active mission are terminal, the mission must not remain in a working status (`approved`, `dispatched`, etc.). Run `cat_sprint_closeout.py`.
7. **MISSION_ID_UNIQUE** — Each `mission_id` appears in at most one contract file under `missions/active`, `backlog`, `archived`, or `examples`.

## Drift codes

| Code | Meaning |
|------|---------|
| `MISSION_ID_MISMATCH` | Tower and registry disagree on active mission |
| `BEAD_ID_MISMATCH` | Tower and registry disagree on active BEAD |
| `REGISTRY_CONTRACT_STATUS_MISMATCH` | Registry status != contract file status |
| `BEAD_NOT_ACTIVE` | Pointer targets queued or non-active BEAD |
| `BEAD_TERMINAL_POINTER` | Pointer targets completed/archived BEAD |
| `TERMINAL_MISSION_ACTIVE` | Active pointer on closed/learned mission |
| `MISSION_BEADS_COMPLETE_MISSION_OPEN` | All BEADs done but mission still open |
| `MISSION_ID_COLLISION` | Duplicate mission_id in contract files |

## Enforcement points

- **CI:** `python scripts/cat_align_check.py --strict` (blocking)
- **GO:** `cat_resolve_go.py` runs alignment check before dispatch
- **Creation:** `cat_new_mission.py` rejects duplicate IDs
- **Validation:** `cat_validate.py --all` includes collision scan

## Post-sprint idle

After `cat_sprint_closeout.py`, tower `status` is `sprint_idle` and `active_mission_id` / `active_bead_id` are empty strings. This is the only valid state with no active mission.
