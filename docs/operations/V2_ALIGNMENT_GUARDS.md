# V2 Alignment Guards Operations

This runbook defines how to execute the Sprint 004 Tower guard checks without mutation.

## Commands

- `python scripts/cat_state_freshness.py --write-report`
- `python scripts/cat_branch_hygiene.py --write-report`
- `python scripts/cat_tower_guard.py --write-report`

## Outputs

- `evidence/tower/state_freshness_report.md`
- `evidence/tower/branch_hygiene_report.md`
- `evidence/tower/tower_guard_report.md`
- `evidence/tower/tower_guard_report.json`

## Guard Behavior

- State freshness checks only compare active mission/bead pointers and contract presence.
- Branch/root hygiene checks are dry-run only and never delete or mutate files.
- Unified tower guard combines both checks and validates report JSON against schema.

## Expected Exit Codes

- `0`: all checks pass and schema validation passes.
- `1`: one or more checks fail, or report JSON fails schema validation.

## Operator Procedure

1. Ensure you are on the session branch and local workspace is available.
2. Run `python scripts/cat_tower_guard.py --write-report`.
3. Review `evidence/tower/tower_guard_report.md` for actionable issues.
4. Use report evidence in BEAD transitions from `in_progress` through `archived`.
5. Do not auto-repair from this guard; all remediation is explicit follow-up work.
