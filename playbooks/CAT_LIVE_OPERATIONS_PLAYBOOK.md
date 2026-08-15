# CAT Live Operations Playbook

## Purpose

This is the production runbook for executing one bounded CAT task from an
official Bead through Wisker dispatch, evidence validation, and official
Bead closure. Codex and Cursor follow the same sequence. CAT governance files
are canonical; this playbook does not create a second task system.

## Authority model

```text
Human goal
  -> approved mission
  -> official Bead (`bd` / Dolt)
  -> derived Wisker packet
  -> scoped execution
  -> evidence bundle
  -> evidence-first closeout
  -> official Bead closure
```

- Official Beads own task identity, dependencies, claims, and lifecycle status.
- Wiskers own bounded execution scope only. They never contain lifecycle status.
- `CAT_MANIFEST.md` and the repository `AGENTS.md` are the policy authority.
- `archive/legacy-cat-state/` is read-only history and is never selected by GO.

## Fresh checkout activation

Run from the repository root:

```powershell
python scripts/cat_beads_init.py
bd prime
bd ready --json
```

`cat_beads_init.py` verifies the pinned official `bd` binary, initializes the
local `.beads/` database when needed, configures the CAT Dolt remote, and does
not modify `AGENTS.md`. `.beads/` is local official Beads state and must never
be used for CAT YAML contracts.

## Start one task

Create a Bead with enough metadata for CAT to derive its Wisker. The metadata
must include `mission_id`, `objective`, `agent_role`, `autonomy_level`,
`confidence`, `risk`, `allowed_paths`, `forbidden_paths`, `tool_budget`,
`definition_of_done`, `validation`, `stop_conditions`, and `required_output`.

```powershell
bd create "Short task title" `
  --description "Why this work exists and what must be done" `
  --type task --priority 2 --json
bd update <id> --claim
bd dolt push
```

For normal GO dispatch, leave the Bead open after creation. The resolver
claims it atomically after it has generated and schema-validated the Wisker.

## Resolve and dispatch

```powershell
python scripts/cat_align_check.py --strict
python scripts/cat_resolve_go.py --check-schema
```

The resolver performs this fail-closed sequence:

1. Read `bd ready --json`.
2. Select deterministically by priority, creation time, and Bead ID.
3. Read the selected Bead with `bd show <id> --json`.
4. Derive `wiskers/packets/WISKER-<bd-id>-<digest-prefix>.yaml`.
5. Validate the Wisker schema and allowed/forbidden paths.
6. Claim the official Bead.
7. Re-read the Bead and verify its source digest did not change.
8. Emit the dispatch packet.

Read the emitted Wisker before editing anything. If `bd` is missing, output is
malformed, no approved mission exists, the source digest is stale, the schema
fails, or a requested path is forbidden, stop without dispatch.

## Execute within scope

The agent may write only paths listed in the selected Wisker. It must not edit
`.beads/`, `.git/`, credentials, archived state, or any path outside the
packet. Keep the required output and validation evidence under the paths
declared by the Wisker.

Do not add a `status` field to a Wisker. A repeated resolution for the same
Bead and source commit must be idempotent; a changed Bead digest must produce
a new Wisker identity and block use of the old packet.

## Evidence-first closeout

Run the validations named by the Wisker, then create and validate an evidence
bundle:

```powershell
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_align_check.py --strict
pytest -q

python scripts/cat_evidence.py create `
  --mission <mission-id> `
  --bead <bead-id> `
  --evidence-id EB-CAT-LIVE-<short-name> `
  --type closeout `
  --result passed `
  --summary "Describe the completed result" `
  --artifact playbooks/<playbook>.md `
  --artifact wiskers/packets/<packet>.yaml `
  --learning "Record the operational learning" `
  --created-by "Codex"

python scripts/cat_evidence.py validate `
  --bundle evidence/bundles/generated/EB-CAT-LIVE-<short-name>.yaml
```

Only after evidence validation succeeds:

```powershell
python scripts/cat_closeout.py `
  --type bead `
  --id <bead-id> `
  --to closed `
  --bundle evidence/bundles/generated/EB-CAT-LIVE-<short-name>.yaml `
  --reason "Evidence validated; task complete" `
  --actor "Codex"
bd dolt push
bd show <bead-id> --json
bd ready --json
```

`cat_closeout.py` validates the evidence bundle before it calls official
`bd close`. `cat_transition.py` is for mission transitions only and must not
be used to mutate Bead lifecycle state.

## Closeout checklist

- [ ] Wisker packet exists and contains the current Bead digest and Git SHA.
- [ ] All work stayed inside `allowed_paths`.
- [ ] Required validation commands passed.
- [ ] Evidence bundle is schema-valid and `closeout_ready: true`.
- [ ] Closeout report exists.
- [ ] Official Bead is `closed` in `bd show <id> --json`.
- [ ] `bd dolt push` completed successfully.
- [ ] `bd ready --json` is empty or contains only unrelated ready work.
- [ ] Git status and the final handoff identify all changed files and evidence.

If any item fails, leave the Bead open or in progress, record the blocker in
Beads, and stop. Never mark completion based only on a Wisker or a local note.
