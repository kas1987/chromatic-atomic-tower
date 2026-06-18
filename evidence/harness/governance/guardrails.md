# Harness Guardrails

## Hard Blocks

The local worker may not perform these actions without explicit approval:

- delete large folders
- rewrite git history
- rotate secrets or access keys
- deploy to production
- call external APIs with real credentials
- change payment, auth, security, persistence, or migration logic without escalation
- modify files outside the ticket's allowed file list

## Required Evidence

Each completed worker task must include:

- ticket ID
- changed files
- diff summary
- commands run
- command outputs or summaries
- known failures
- worker self-assessment
- cheap review notes

## Merge Gate

A patch may be considered for merge only when:

- acceptance criteria are met
- required tests pass or exceptions are documented
- Opus final review returns `APPROVE`
- human approval is given
