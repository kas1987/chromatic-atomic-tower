# Agent Instructions

This file is for ChatGPT, Claude, Cursor, Codex, and any other agent operating inside CAT.

## Required read order

Before acting, read only this minimum set:

1. `CAT_MANIFEST.md`
2. `CHROMATIC_TREES.md`
3. `state/TOWER_STATE.yaml`
4. `missions/registry/MISSION_REGISTRY.yaml`
5. the active BEAD file selected by `scripts/cat_resolve_go.py`
6. the role file matching your assigned role in `agents/roles/`

Do not read the whole repo unless a BEAD explicitly allows audit or migration work.

## Action rules

- Do not mutate files without a Mission ID and BEAD ID.
- Do not touch files outside BEAD `allowed_paths`.
- Do not touch BEAD `forbidden_paths`.
- Do not expand scope.
- Do not invent new missions during implementation.
- Do not close work without evidence.
- Do not promote yourself.
- Exception: human-invoked operator-plane meta-work (sprint closeouts, retrospectives, kickoffs, repo hygiene) is exempt from the `allowed_paths` rule per `CAT_MANIFEST.md` §6.1, must be logged in `learnings/DECISION_LOG.md`, and still must not touch `forbidden_paths`.
- Stop if confidence drops below the BEAD threshold.

## Output format

Every agent response must include:

```md
## CAT Agent Result

Mission:
BEAD:
Role:
Confidence:
Risk:
Files Read:
Files Changed:
Validation:
Evidence:
Result:
Next Recommended Action:
Stop Conditions Hit:
```

## GO command interpretation

When the human says `GO`, do not improvise. Run or simulate:

```bash
python scripts/cat_resolve_go.py
```

Then execute only the returned BEAD.
