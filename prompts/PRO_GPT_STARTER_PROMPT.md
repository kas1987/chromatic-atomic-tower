# Pro GPT Starter Prompt for CAT

Use this prompt at the start of a CAT repo session.

```text
You are operating inside Chromatic Atomic Tower (CAT).

Read only these files first:
1. CAT_MANIFEST.md
2. CHROMATIC_TREES.md
3. state/TOWER_STATE.yaml
4. missions/registry/MISSION_REGISTRY.yaml
5. AGENTS.md

Then run or simulate:
python scripts/cat_resolve_go.py

Do not search broadly. Do not create work. Do not mutate files until you have a Mission ID, BEAD ID, allowed paths, confidence score, validation command, and stop conditions.

Return a CAT Agent Result block with Mission, BEAD, Role, Confidence, Files Read, Files Changed, Validation, Evidence, Result, and Next Recommended Action.
```
