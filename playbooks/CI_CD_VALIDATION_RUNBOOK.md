# CI/CD Validation Runbook

## CI validation

CI proves the repo is safe enough to merge.

Required checks:

- repo health
- CAT schema validation
- Harness alignment validation
- Mermaid fence validation
- tests
- evidence artifact upload
- cost guard: Balanced by default; Strict for workflow, gate, or guard changes

## CD promotion

CD proves the mission is safe enough to release or promote.

Required checks:

- evidence bundle exists
- confidence score meets threshold
- M4 approval is recorded if applicable
- rollback or replan path exists
- exceptions are disclosed

The canonical default branch is `master`. Cost-guard results are uploaded as
exact-head JSON evidence and must not be inferred from seat presence or prior
workflow output.

## Promotion thresholds

| Score | Decision |
|---:|---|
| 90-100 | eligible for auto-proceed if not M4 |
| 70-89 | human-approved proceed |
| 50-69 | self-heal / remediation BEAD |
| 0-49 | block and replan |
