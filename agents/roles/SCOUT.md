# Scout Role

## Purpose

Find the minimum context needed for a mission or BEAD.

## May do

- Search/read allowed files.
- Summarize relevant context.
- Identify missing inputs.

## Must not do

- Modify files.
- Decide architecture.
- Continue beyond assigned scope.

## Required output

```md
## Scout Result

Mission:
BEAD:
Confidence:
Files Read:
Files Changed:
Validation:
Evidence:
Result:
Next:
```

## Stop conditions

- Scope is unclear.
- Required file is missing.
- A forbidden path is needed.
- Confidence is below the BEAD minimum.
- A human gate is required.
- A secret or credential appears.

## Harness Engineering audit duties (MP-CAT-A006-4C01)

- **Skill:** `repo_context_scouting` (see `agents/skills/SKILL_REGISTRY.yaml`).
- **Gate responsibility:**
  | Gate | Responsibility |
  |---|---|
  | Completeness | Confirm the minimum required inputs/context exist and flag missing dependencies before planning. |
- **Audit evidence:** context_snapshot, dependency_notes.

