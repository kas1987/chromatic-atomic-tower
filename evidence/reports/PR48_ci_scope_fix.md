# PR #48 CI Scope Fix

Mission: MP-CAT-A020-4C01 (post-closeout operator-plane repair)

The `cat_pr_check.py` closeout classifier correctly recognized PR #48 as a
mission closeout, but its generic lifecycle-path allowlist omitted the exact
A020 contract deliverables in `schemas/`, `scripts/`, and the root roadmap.

The repair adds only those explicit files to `CLOSEOUT_EXTRA_FILES`. Whole
`schemas/` and `scripts/` directories remain outside closeout scope, so an
unrelated contract or automation file still fails the check.

Validation:

- `python -m pytest tests/test_cat_pr_check_extended.py -q`
- `python scripts/cat_pr_check.py --changed-files <PR #48 changed-file list>`
