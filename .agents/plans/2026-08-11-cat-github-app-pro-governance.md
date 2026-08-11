# MP-CAT-A027-4C01 — GitHub App Access and Pro Governance Hardening

Planning-only packet prepared by Terra review at exact source HEAD
`e3fd14a3bae86f6e3e16abd179a53dcc7609e385`.

## Hold boundary

This branch registers a draft mission and six queued beads. It does not activate
A027, move the active A026 pointer, run GO, implement code, read secrets, or
change GitHub settings. The first deferred GO is BEAD-CAT-A027-4C01-01 and is
read-only, subject to explicit approval after this planning PR is reviewed.

## Dependency order

`01 → (02, 03, 04) → 05 → 06`

Beads 02–04 may be planned independently after the access-boundary contract;
05 reconciles their outputs before any remote policy proposal; 06 records the
resulting governance telemetry.

## Known baseline

- Repository: `kas1987/chromatic-atomic-tower`, default branch `master`.
- Local `@owner` CODEOWNERS entries are unresolved by GitHub’s CODEOWNERS API.
- Local strict cost guard passes the eight local workflows.
- Remote protection currently requires `validate` and `cat-ci` only; review,
  conversation-resolution, and administrator enforcement are not enabled.
- Connected GitHub App access is present, but the local self-owned App helper
  has no configured ID/private-key path in this checkout.

## Pre-mortem controls

Every report binds owner, repository ID/name, installation ID, default branch,
and exact HEAD. Credential-bearing paths remain forbidden. Draft-aware CI must
retain canonical checks. Protection application is a separate human decision.
