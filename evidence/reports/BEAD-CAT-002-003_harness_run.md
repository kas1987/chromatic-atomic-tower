# Evidence Report: BEAD-CAT-002-003 — Harness Run

- Mission: derived from BEAD-CAT-002-003
- BEAD: BEAD-CAT-002-003
- Ticket: DEMO-001
- Type: harness_run
- Validation result: passed
- Created by: scripts/harness_bridge.py
- Created at: 2026-06-17T17:30:21Z

## Summary

Harness run for ticket `DEMO-001` (BEAD `BEAD-CAT-002-003`) completed with tests **passed**
(review_packet.md 'Test passed:' line). The BEAD was moved to `queued -> validating` and the queue item to
`review`. Status was NOT set to a terminal/done state — human approval still gates merge.

## Files changed (worker diff, names only)

```text
scripts/harness_demo.py
```

## Test results

```text
..............                                                           [100%]
14 passed in 0.03s
```

## Artifacts

| Artifact | Path |
|---|---|
| Review packet | `.agent/runs/DEMO-001/review_packet.md` |
| Worker response | `.agent/runs/DEMO-001/worker_response.md` |
| Cheap review | `.agent/runs/DEMO-001/cheap_review.md` |
| Test output | `.agent/runs/DEMO-001/test_output.txt` |
| Git diff (full) | `.agent/runs/DEMO-001/git_diff_full.txt` |
| Evidence report | `evidence/reports/BEAD-CAT-002-003_harness_run.md` |

## Validation

```bash
python scripts/cat_validate.py --all
```

## Note on confidence

`confidence.current` on the BEAD is human-owned and is intentionally NOT auto-mutated by the
bridge. Re-score it during human/Opus review using this evidence.
