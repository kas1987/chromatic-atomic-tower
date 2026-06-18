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

## CD promotion

CD proves the mission is safe enough to release or promote.

Required checks:

- evidence bundle exists
- confidence score meets threshold
- M4 approval is recorded if applicable
- rollback or replan path exists
- exceptions are disclosed

## Promotion thresholds

| Score | Decision |
|---:|---|
| 90-100 | eligible for auto-proceed if not M4 |
| 70-89 | human-approved proceed |
| 50-69 | self-heal / remediation BEAD |
| 0-49 | block and replan |
