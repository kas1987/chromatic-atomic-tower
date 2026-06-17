# V2 Alignment Guards Operations

This runbook defines how to execute the Sprint 004 Tower guard checks without mutation.

## Commands

- `python scripts/cat_state_freshness.py --write-report`
- `python scripts/cat_branch_hygiene.py --write-report`
- `python scripts/cat_tower_guard.py --write-report`
- `python scripts/cat_root_hygiene_strict.py`
- `python scripts/cat_root_hygiene_strict.py --mode warn` (builder mode)
- `python scripts/cat_root_hygiene_strict.py --kill-switch` (temporary emergency bypass)

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

## Root Cleanliness Policy

- Repository root must only contain entries allowed by `gates/hygiene/root_allowlist.yaml`.
- Any non-allowlisted root file or directory is treated as a hygiene failure.
- Standard validation (`python scripts/cat_validate.py --all`) enforces this check.

### Enforcement Modes

- `enforce`: hygiene issues fail validation.
- `warn`: hygiene issues are reported but do not fail validation.
- `off`: skip root hygiene enforcement.

Mode controls:

- CLI: `python scripts/cat_validate.py --all --root-hygiene-mode warn`
- Env var: `CAT_ROOT_HYGIENE_MODE=enforce|warn|off`
- Emergency kill switch: `CAT_HYGIENE_KILL_SWITCH=1` or `--kill-switch`

### Root Hygiene Remediation

1. Detect drift and auto-clean known transient root cache artifacts: `python scripts/cat_root_hygiene_strict.py --mode warn`
2. Review report: `evidence/tower/branch_hygiene_report.md`
3. Manual fallback - remove known transient pytest root caches (safe no-op when absent):

```powershell
Get-ChildItem -Name | Where-Object { $_ -like 'pytest-cache-files-*' } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
```

4. Re-run strict validation: `python scripts/cat_root_hygiene_strict.py`
