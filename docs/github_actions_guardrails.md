# CAT GitHub Actions Guardrails

## Overview

`scripts/cat_cost_guard.py` enforces cost and security policies on all GitHub Actions workflow files under `.github/workflows/`.

Two severity levels:
- **FAILURE** — workflow is blocked; CI exits nonzero
- **WARNING** — printed but not blocking (unless `--strict` is passed)

## Rules

### FAILURE: Schedule trigger without approval

Any workflow with a `schedule:` trigger must include the annotation:

```yaml
# CAT_BUDGET_APPROVED
```

anywhere in the file. Scheduled runs consume Actions minutes continuously and must be explicitly budget-approved.

### FAILURE: Risky runner without exception

Workflows using `windows-latest` or `macos-latest` runners must include:

```yaml
# CAT_RUNNER_EXCEPTION: <reason>
```

Windows and macOS runners cost 2× and 10× the Linux rate respectively. Ubuntu-latest is the default.

### WARNING: Missing permissions block

Every workflow should declare explicit permissions to limit the default `GITHUB_TOKEN` scope:

```yaml
permissions:
  contents: read
```

### WARNING: Missing concurrency block

Long-running workflows should cancel outdated runs:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### WARNING: Missing timeout-minutes

Every job should have a timeout to prevent runaway billing:

```yaml
jobs:
  build:
    timeout-minutes: 15
```

## Commands

### Check all workflows

```bash
python scripts/cat_cost_guard.py --check
```

Exits 0 if no failures; exits 1 if any failures exist.

### Strict mode (warnings as failures)

```bash
python scripts/cat_cost_guard.py --check --strict
```

Exits 1 if any warnings or failures exist. Useful for enforcing full hardening.

## validate-cat.yml hardening

The `validate-cat.yml` workflow itself meets all guardrail requirements:

```yaml
permissions:
  contents: read

concurrency:
  group: validate-cat-${{ github.ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
```

## Integration

`cat_cost_guard.py` is called in CI via `validate-cat.yml` to ensure no new workflows bypass cost controls.
