# CI Governance Checklist

## Required Before Merge

- [ ] Mission ID present.
- [ ] BEAD ID present.
- [ ] Mission Pack validates.
- [ ] BEAD validates.
- [ ] Registry validates.
- [ ] Tower state validates.
- [ ] Evidence bundles validate or are not required.
- [ ] Tests pass.
- [ ] Changed files are allowed by BEAD scope.
- [ ] No forbidden paths changed.
- [ ] CI report generated.
- [ ] Failure classification exists for any failed check.
- [ ] Human gate was not bypassed.

## Self-Healing Review

- [ ] Dry-run reviewed.
- [ ] Repair class is allowed.
- [ ] No secret, production, evidence, or state mutation repair attempted.
- [ ] Apply mode approved if used.
