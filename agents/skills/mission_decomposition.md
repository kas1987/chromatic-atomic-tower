# Mission Decomposition Skill

## Intent

Translate a mission objective into atomic, dispatchable BEADs with explicit scope,
acceptance criteria, and validation plan.

## Inputs

- Mission Pack (mission YAML contract)
- CAT manifest and ID naming convention
- Prior mission BEADs (for sequence continuity)
- Complexity matrix (for model routing hints)

## Steps

1. Read the mission contract and identify all stated deliverables.
2. Group deliverables into atomic units — each BEAD must have one objective,
   one allowed-paths scope, and one definition of done.
3. Assign a two-digit sequence number (`01`, `02`, ...) and derive the BEAD ID
   from the mission stem (e.g. `BEAD-CAT-A006-4C01-01`).
4. For each BEAD, specify: `allowed_paths`, `forbidden_paths`, `validation` steps,
   `required_output` artifacts, and `definition_of_done`.
5. Verify all BEADs are referenced in the mission contract's `beads` list.
6. Confirm complexity level and propose model routing per `agents/model_routes.yaml`.

## Evidence

- list of BEAD IDs and titles with scope summary
- mission YAML updated with `beads` list
- validation plan for each BEAD
