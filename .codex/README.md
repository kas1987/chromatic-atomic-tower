# CAT Codex activation

Codex uses the repository root `AGENTS.md` as the canonical policy. This file is
only a pointer so the Codex surface does not grow a second rule system.

Before substantive work:

```text
python scripts/cat_beads_init.py
bd prime
bd ready --json
python scripts/cat_resolve_go.py --check-schema
```

Read the emitted packet under `wiskers/packets/`. Official Beads own status;
Wiskers define the bounded scope. Closeout evidence is validated before `bd
close` is called.
