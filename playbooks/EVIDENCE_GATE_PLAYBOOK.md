# Evidence Gate Playbook

## Purpose

This playbook governs how CAT validates proof before BEAD or mission completion.

## Core Rule

```text
No Evidence Bundle = No Completion
```

## Required Inputs

| Input | Required |
|---|---:|
| Mission or BEAD ID | Yes |
| Evidence bundle | Yes |
| Required artifact paths | Yes |
| Validation result | Yes |
| Learning note | Yes |
| Closeout reason | Yes |

## Execution Loop

```text
Inspect target -> Validate bundle schema -> Verify artifacts -> Check validation result -> Write report -> Log event -> Transition state
```

## Decision Rules

| Condition | Decision |
|---|---|
| Bundle schema invalid | Block |
| Required artifact missing | Block |
| Required validation failed | Block |
| Target ID mismatch | Block |
| Learning note missing | Block |
| Evidence valid and transition allowed | Proceed |

## Agent Instructions

Agents must not claim completion unless the evidence gate passes.

Agents may prepare evidence bundles but should not apply closeout for high-risk or irreversible missions without approval.

## Review Checklist

- [ ] Bundle validates against schema.
- [ ] Bundle references correct mission and BEAD.
- [ ] Required artifact paths exist.
- [ ] Required validation passed.
- [ ] Closeout report was written.
- [ ] Closeout event was logged.
- [ ] Transition event was logged.
- [ ] Learning note is present.
