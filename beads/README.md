# BEADs

A BEAD is the smallest safe dispatchable unit of work.

A good BEAD has:

- one objective
- one mission parent
- explicit allowed files
- explicit forbidden files
- a tool budget
- stop conditions
- validation
- evidence output
- definition of done

Bad BEAD: `Improve the repo.`

Good BEAD: `Add mission schema validation to scripts/cat_validate.py and prove it with one example.`

## Naming Convention (New Work)

- New bead IDs use mission-stem format: `BD-CAT-S001-4C01-01`
- Beads inherit mission stem from `MP-CAT-S001-4C01`
- Last segment is a two-digit bead sequence (`01`, `02`, ...)
- Legacy bead IDs remain valid only for grandfathered legacy missions below cutover
