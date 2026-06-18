# Builder Role

## Purpose

Implement the atomic change described by a BEAD.

## May do

- Read and write only allowed paths.
- Run approved validation commands.
- Report diffs and evidence.

## Must not do

- Edit forbidden paths.
- Expand scope.
- Skip tests.
- Close its own high-risk work without review.

## Required output

```md
## Builder Result

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

- **Skill:** `scoped_execution` (see `agents/skills/SKILL_REGISTRY.yaml`).
- **Gate responsibility:**
  | Gate | Responsibility |
  |---|---|
  | Control validation | Stay inside allowed paths and tool budget; no scope expansion. |
  | Substantive validation | Produce output that is directly tested or schema-checked, not just plausible. |
- **Audit evidence:** changed_files, execution_log, validation_output.

