# GO Mode Playbook

## Meaning of GO

`GO` means advance the next approved, unblocked, highest-priority **active** BEAD.

It does not mean broad exploration.

## Pre-GO alignment gate (MP-CAT-A008-4C01)

```bash
python scripts/cat_align_check.py --strict
```

`cat_resolve_go.py` runs this automatically. GO is blocked on any drift.

## Resolver steps

1. Run alignment check (tower ↔ registry ↔ contracts).
2. Read mission registry; select approved mission.
3. Read active BEADs in `beads/active/`.
4. Select `active` BEAD (not `queued` unless `--allow-queued` for kickoff).
5. Cross-check tower `active_bead_id` when set.
6. Check confidence; print dispatch packet.
7. Execute only returned scope.

## Commands

```bash
python scripts/cat_align_check.py --strict   # pre-flight
python scripts/cat_resolve_go.py
python scripts/cat_resolve_go.py --allow-queued   # operator kickoff only
```

## References

- [STATE_ALIGNMENT_PLAYBOOK.md](STATE_ALIGNMENT_PLAYBOOK.md)
- [docs/architecture/STATE_ALIGNMENT.md](../docs/architecture/STATE_ALIGNMENT.md)
