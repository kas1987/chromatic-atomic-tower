# GitHub Bridge

The GitHub Bridge maps GitHub work units into CAT governance.

## Governed Objects

- Issue intake
- Branch name
- Commit message
- Pull request title
- Changed files
- CI report
- Evidence report

## Required Trace Tokens

```text
[MP-CAT-A010-4C01]
[BEAD-CAT-A010-4C01-01]
```

Legacy missions 000 through 005 may continue using:

```text
[MP-CAT-###]
[BEAD-CAT-###-###]
```

## Valid Branch Example

```text
feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract
```

## Valid PR Title Example

```text
[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract
```

## Rule

A PR that cannot be traced to a Mission Pack and BEAD is orphan work and must not be promoted.
