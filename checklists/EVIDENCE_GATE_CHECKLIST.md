# Evidence Gate Checklist

## Before Closeout

- [ ] Target mission or BEAD ID is correct.
- [ ] Evidence bundle exists.
- [ ] Evidence bundle validates against schema.
- [ ] Required artifact paths exist.
- [ ] Required validation result is passed or intentionally skipped.
- [ ] No required artifact is marked failed or blocked.
- [ ] Learning note is present.
- [ ] Closeout reason is specific.
- [ ] Dry-run closeout was performed.

## After Closeout

- [ ] Closeout report exists.
- [ ] Closeout event exists in `evidence/logs/closeouts.jsonl`.
- [ ] Transition event exists in `evidence/logs/transitions.jsonl`.
- [ ] Mission registry remains coherent.
- [ ] Tower state remains coherent.
- [ ] Next BEAD is queued or mission is ready for review.
