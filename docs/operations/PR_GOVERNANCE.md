# PR Governance

## Required Checks

1. PR title includes Mission ID and BEAD ID.
2. Branch name includes Mission ID and BEAD ID.
3. Commit message includes Mission ID and BEAD ID.
4. Changed files are inside BEAD `allowed_paths`.
5. No forbidden path is changed.
6. Evidence report exists before closeout.

## Failure Handling

| Failure | Response |
|---|---|
| Missing Mission ID | Block PR and request correction |
| Missing BEAD ID | Block PR and request correction |
| Changed file outside scope | Block PR or create new BEAD |
| Forbidden path change | Halt and escalate |
| Evidence missing | Do not closeout |
