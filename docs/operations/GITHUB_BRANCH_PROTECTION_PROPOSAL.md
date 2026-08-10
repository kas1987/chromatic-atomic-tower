# CAT Master Branch Protection Proposal

This is a human-applied GitHub policy proposal. CAT automation must not mutate
branch protection, repository settings, secrets, PRs, or branches.

## Required remote policy

For `kas1987/chromatic-atomic-tower:master`:

- Require the current canonical validation contexts: `validate`, `cat-ci`,
  `CAT Governance CI`, and `LOGHOUSE CI`.
- Require at least one human approving review.
- Require conversation resolution.
- Enforce the policy for administrators.
- Keep force pushes and branch deletion disabled.
- Keep human merge authority; no automatic merge action is authorized by this
  mission.

The exact GitHub check context names must be confirmed from recent successful
runs before applying the settings. The read-only command is:

```text
python scripts/cat_branch_protection_audit.py --repo kas1987/chromatic-atomic-tower --branch master --output evidence/reports/ci-cd-remediation/BEAD-06.json
```

## Negative-test procedure

After a human applies the policy, create or identify a disposable PR that:

1. lacks the required human approval;
2. leaves one required conversation unresolved; or
3. has one required status context missing or failing.

The PR must remain non-promotable. A compliant control test must satisfy every
required context and approval, resolve all conversations, and then become
eligible for human merge. Do not use `--admin`, force-push, or automatic merge
to make the negative test pass.

## Current finding

The 2026-08-10 read-only snapshot showed only `validate` and `cat-ci` required,
zero required reviews, conversation resolution disabled, and administrator
enforcement disabled. This is a policy gap, not a local workflow failure.
