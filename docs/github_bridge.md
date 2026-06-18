# CAT GitHub Bridge

## Overview

The CAT GitHub Bridge ensures every pull request and issue in the repository is traceable to a Mission and BEAD. It consists of:

- **`.github/pull_request_template.md`** — PR template requiring Mission ID, BEAD ID, validation output, and evidence path
- **`.github/ISSUE_TEMPLATE/mission_request.md`** — Issue template for requesting a new CAT mission
- **`.github/ISSUE_TEMPLATE/bead_task.md`** — Issue template for tracking a BEAD implementation
- **`scripts/cat_pr_guard.py`** — Local validator for PR bodies

## PR Template Fields

Every PR must include:

| Field | Format | Example |
|---|---|---|
| Mission ID | `MP-CAT-XXXX-XCXX` | `MP-CAT-A014-4C01` |
| BEAD ID | `BEAD-CAT-XXXX-XCXX-NN` | `BEAD-CAT-A014-4C01-05` |
| Evidence path | `evidence/...` | `evidence/reports/pr-guard-pytest-output.txt` |
| Validation output | paste of `cat_validate.py --all` | `CAT validation passed.` |

## Commands

### Validate a PR body

```bash
python scripts/cat_pr_guard.py --check-pr "$(cat /tmp/pr_body.txt)"
```

### Check template files exist

```bash
python scripts/cat_pr_guard.py --check-templates
```

### Run built-in pass/fail samples

```bash
python scripts/cat_pr_guard.py --check-samples
```

Returns exit 0 if all samples behave as expected (valid passes, invalid rejects).

## Issue Templates

### mission_request.md

Used to request a new CAT mission. Fields: Objective, Why this matters, Suggested complexity (M1–M4), Scope in/out, Risks, Validation idea, Human gate.

### bead_task.md

Used to track a BEAD implementation. Fields: BEAD ID, Mission ID, Objective, Allowed paths, Definition of done, Evidence required, Validation commands.

## Integration

`cat_pr_guard.py` can be added to a local git pre-push hook or called manually before opening a PR. It is not enforced in CI (CIs can't read the PR body at push time), but it is run as part of BEAD-05 validation.
