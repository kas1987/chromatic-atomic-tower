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
