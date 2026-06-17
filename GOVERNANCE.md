# Governance

CAT governance is simple:

1. Use the lowest mission complexity that safely fits.
2. Require mission and BEAD contracts before execution.
3. Apply gates before mutation.
4. Validate before closeout.
5. Record learning before moving on.

## Required approvals

Human approval is required for:

- M4 missions
- production deployment
- secrets or credentials
- destructive actions
- irreversible changes
- cross-repo mutation
- public release
- cost-bearing external services
- security-sensitive changes

## Review tiers

| Mission level | Review requirement |
|---|---|
| M1 | Self review or reviewer |
| M2 | Reviewer recommended, required before closeout if code changed |
| M3 | Reviewer and auditor |
| M4 | Human gate, reviewer, auditor, and security if applicable |
