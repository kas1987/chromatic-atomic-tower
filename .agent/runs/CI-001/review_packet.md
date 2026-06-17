# Review Packet

## Ticket

# Ticket: CI-001 Add pytest to CI and fix push trigger

## Priority
p1

## Objective

Update `.github/workflows/validate-cat.yml` so the `validate` job ALSO runs the pytest
suite, and so the `push` trigger targets the real default branch `master` (not `main`).

## Context

The CAT CI workflow currently runs cat_check_repo, cat_validate --all, and cat_resolve_go,
but NOT pytest — so test regressions are not caught by CI. The push trigger also targets
`main`, but the repository's default branch is `master`, so push CI never fires.

Current file contents:

```yaml
name: Validate CAT

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python scripts/cat_check_repo.py
      - run: python scripts/cat_validate.py --all
      - run: python scripts/cat_resolve_go.py
```

Required changes:
1. Change `push.branches` from `[main]` to `[master]`.
2. Add a final step `- run: python -m pytest -q` after the cat_resolve_go step.
3. Keep everything else identical (name, pull_request trigger, checkout, setup-python 3.11, pip install).

## Allowed Files

- `.github/workflows/validate-cat.yml`

## Blocked Actions

- Do not modify files outside the allowed list.
- Do not change dependencies, add caching, or alter Python version.
- Do not perform destructive actions.

## Required Commands

```bash
python -m pytest -q tests/test_ci_workflow.py
```

## Output Required

- Complete contents of `.github/workflows/validate-cat.yml` as a FILE block
- Worker summary
- Known risks

## Acceptance Criteria

- `.github/workflows/validate-cat.yml` is valid YAML.
- The `validate` job includes a step running `pytest`.
- The `push` trigger includes `master`.
- `pull_request` trigger and all existing steps are preserved.
- All tests in `tests/test_ci_workflow.py` pass.

## Stop Conditions

Stop and report if:

- The workflow cannot be expressed as valid YAML.
- The change would require editing a file other than the workflow.
- The required test cannot be satisfied by the described change.


## Files Changed

```text
.github/workflows/validate-cat.yml

```

## Diff Summary

```text
 .github/workflows/validate-cat.yml | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)

```

## Patch / Targeted Diff

```diff
diff --git a/.github/workflows/validate-cat.yml b/.github/workflows/validate-cat.yml
index d4bf4d1..1b228b1 100644
--- a/.github/workflows/validate-cat.yml
+++ b/.github/workflows/validate-cat.yml
@@ -3,7 +3,7 @@ name: Validate CAT
 on:
   pull_request:
   push:
-    branches: [main]
+    branches: [master]
 
 jobs:
   validate:
@@ -17,3 +17,4 @@ jobs:
       - run: python scripts/cat_check_repo.py
       - run: python scripts/cat_validate.py --all
       - run: python scripts/cat_resolve_go.py
+      - run: python -m pytest -q

```

## Test Commands Run

```text
python -m pytest -q tests/test_ci_workflow.py
```

## Test Results

```text
...                                                                      [100%]
3 passed in 0.04s

```

## Worker Self-Assessment

Worker model: kimi-k2.7-code:cloud
Attempts used: 1 / 2
Files written: ['.github/workflows/validate-cat.yml']
Guardrail violations: []
Escalation notes: ["Sensitive flags on attempt 1: ['Sensitive pattern: pip\\\\s+install\\\\b']"]

## Cheap Reviewer Notes

```markdown
# Cheap Review

## Decision
APPROVE

## Findings
- None. The diff precisely implements both required changes.

## Evidence Check
- **Diff vs. ticket requirement 1**: `branches: [main]` → `branches: [master]` is present at line 6 of the diff. ✅
- **Diff vs. ticket requirement 2**: `- run: python -m pytest -q` is added as the final step after `cat_resolve_go.py`. ✅
- **Preservation check**: Diff context lines show `name: Validate CAT`, `pull_request:` trigger, `actions/checkout@v4`, `actions/setup-python@v5` with `python-version: "3.11"`, and `pip install -r requirements.txt` are all untouched. ✅
- **Test results**: 3 passed in `tests/test_ci_workflow.py` per the worker. ✅
- **Guardrail violations**: None reported. ✅
- The reconstructed final file is valid YAML (proper indentation, list syntax, step ordering).

## Scope Drift Check
- Only `.github/workflows/validate-cat.yml` modified. ✅
- No changes to dependencies, no caching added, Python version unchanged at 3.11. ✅
- No destructive actions evident.

## Test Coverage Check
- The targeted test `tests/test_ci_workflow.py` passed (3/3). The ticket's stop condition is not triggered (workflow is valid YAML, only the allowed file was edited, and the required test passes).

## Recommended Next Action
- Merge the patch. The change is minimal, correct, and fully satisfies the ticket. Minor follow-up (not blocking): the worker did not include the "Complete contents...as a FILE block" deliverable requested in the Output Required section, but the diff is sufficient evidence of correctness.
```

## Known Failures / Exceptions

Test passed: True
Guardrail violations: None
Escalation notes: ["Sensitive flags on attempt 1: ['Sensitive pattern: pip\\\\s+install\\\\b']"]

## Request to Opus

Approve, request revision, or reject this patch. Identify blocking issues and required revisions.
