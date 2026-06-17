# GO Mode Playbook

## Meaning of GO

`GO` means advance the next approved, unblocked, highest-priority BEAD.

It does not mean broad exploration.

## Resolver steps

1. Read mission registry.
2. Select approved mission.
3. Read active BEADs.
4. Select mission current BEAD.
5. Check confidence.
6. Print dispatch packet.
7. Execute only returned scope.

## Command

```bash
python scripts/cat_resolve_go.py
```
