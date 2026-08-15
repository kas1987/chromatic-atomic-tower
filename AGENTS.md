# Agent Instructions

This file is for ChatGPT, Claude, Cursor, Codex, and any other agent operating inside CAT.

## Required read order

Before acting, read only this minimum set:

1. `CAT_MANIFEST.md`
2. `CHROMATIC_TREES.md`
3. `state/TOWER_STATE.yaml`
4. `missions/registry/MISSION_REGISTRY.yaml`
5. the active Wisker packet selected by `scripts/cat_resolve_go.py` (the packet includes the official `bd_id`)
6. the role file matching your assigned role in `agents/roles/`

Do not read the whole repo unless a BEAD explicitly allows audit or migration work.

## Action rules

- Do not mutate files without a Mission ID and official Beads ID.
- Do not touch files outside the selected Wisker `allowed_paths`.
- Do not touch Wisker `forbidden_paths`.
- Do not expand scope.
- Do not invent new missions during implementation.
- Do not close work without evidence.
- Do not promote yourself.
- Exception: human-invoked operator-plane meta-work (sprint closeouts, retrospectives, kickoffs, repo hygiene) is exempt from the `allowed_paths` rule per `CAT_MANIFEST.md` §6.1, must be logged in `learnings/DECISION_LOG.md`, and still must not touch `forbidden_paths`.
- Stop if confidence drops below the Wisker threshold or the source Bead digest changes.

## Task and execution authority

- Official Beads (`bd` backed by Dolt in `.beads/`) owns tasks, dependencies,
  claims, and lifecycle status. Run `bd prime` before substantive work.
- Wiskers (`wiskers/`) are CAT-owned derived execution contracts. They pin an
  official `bd_id` to a source Bead digest and Git commit, and define scope,
  role, risk, tools, validation, and stop conditions.
- Wiskers never carry a lifecycle `status` field. Do not create or update a
  parallel Wisker status.
- Legacy `BEAD-CAT-*` YAML is historical only under `archive/legacy-cat-state/`.
  Runtime code must not select or mutate it.

## Output format

Every agent response must include:

```md
## CAT Agent Result

Mission:
Official Bead:
Wisker:
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

Then read the returned Wisker and execute only within its scope. Closeout must
validate CAT evidence before closing the official Bead.
