# GitHub Bridge Playbook

## Purpose

Govern how GitHub branches, pull requests, commits, issue intake, and changed files bind to CAT Mission Packs and BEADs.

## Operating Loop

```text
Observe GitHub metadata -> Extract Mission + BEAD -> Validate scope -> Emit evidence -> Gate promotion
```

## Dispatch Rule

No Builder or automated agent may proceed on GitHub work unless the branch, PR title, commit message, and changed files can be validated against a Mission Pack and BEAD.

## Stop Conditions

- Missing Mission ID
- Missing BEAD ID
- Changed file outside BEAD allowed paths
- Forbidden path changed
- Secret handling requested
- Repository settings mutation requested
