# Start Here

Use this file when opening the repo for the first time.

## Step 1: Read in this order

1. `README.md`
2. `PDR_CAT_000_ESTABLISH_CORE_REPO.md`
3. `CAT_MANIFEST.md`
4. `CHROMATIC_TREES.md`
5. `state/SPRINT_STATE.md`
6. `missions/registry/MISSION_REGISTRY.yaml`
7. `beads/active/BEAD-CAT-000-001.yaml`
8. `docs/operations/GO_MODE.md`
9. `prompts/PRO_GPT_STARTER_PROMPT.md`

## Step 2: Validate the foundation

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

## Step 3: Resolve the next action

```bash
python scripts/cat_resolve_go.py
```

## Step 4: Commit only after validation

Use this commit pattern:

```text
[MISSION_ID][BEAD_ID] Clear imperative summary
```

Example:

```text
[MP-CAT-000][BEAD-CAT-000-001] Establish CAT core repo skeleton
```
