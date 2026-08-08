# A019 Rollback Record

Mission: MP-CAT-A019-4C01  
BEAD: BEAD-CAT-A019-4C01-04

## Baseline

- Repository: C:/.01_CAT
- Branch: chore/ci-hardening
- Baseline HEAD: c50b79dd0e49950024cc7e18d60c2f769d1b1ac5
- Upstream: origin/chore/ci-hardening
- Baseline divergence: ahead 0 / behind 0

## Preservation reference

- Selective preservation stash: d203c0ff8a7eb01f448c1e51542b083d6c063e4b
- Message: CAT A019 preserve pre-existing A015 and A007 work
- Restore command: git stash apply stash@{0}

The stash contains only explicitly selected pre-existing A015/A007 paths.
A019 mission, bead, role, state, registry, roadmap, logs, evidence, and
transitions remain in the worktree. No branch, worktree, commit, or remote
state was deleted or rewritten.
