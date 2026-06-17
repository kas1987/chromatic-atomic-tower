# Self-Review: BEAD-CAT-002-005 — Evidence Relocation

- Mission: MP-CAT-002 — Multi-Model Coding Harness MVP
- BEAD: BEAD-CAT-002-005 — Relocate durable harness evidence into the evidence plane
- Agent role: Builder
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Relocated DEMO-001 run artifacts from `.agent/runs/DEMO-001/` (transient scratch) to `evidence/runs/DEMO-001/` (durable, tracked evidence plane). Updated `scripts/harness_bridge.py` to automatically copy run artifacts to the evidence plane on every future bridge call. Updated `.gitignore` to explicitly ignore `.agent/runs/` only. Updated the existing evidence report to reference the new paths.

## Files Changed

| File | Action | Summary |
|------|--------|---------|
| `scripts/harness_bridge.py` | modified | Added `copy_durable_artifacts()`, `EVIDENCE_RUNS_DIR`, artifact copy step, updated report paths |
| `.gitignore` | modified | Added explicit `.agent/runs/` ignore, preserved `evidence/runs/` as tracked |
| `evidence/reports/BEAD-CAT-002-003_harness_run.md` | modified | Updated artifact paths → `evidence/runs/DEMO-001/` |
| `evidence/runs/DEMO-001/` | created | 10 durable artifacts copied from `.agent/runs/DEMO-001/` |

## Definition of Done

- [x] Durable artifacts live under `evidence/runs/DEMO-001/` and are tracked (not gitignored)
- [x] `scripts/harness_bridge.py` writes artifacts to `evidence/runs/` on every run
- [x] `evidence/reports/BEAD-CAT-002-003_harness_run.md` points to `evidence/runs/DEMO-001/` paths
- [x] `.gitignore` ignores only `.agent/runs/` transient scratch, not `evidence/runs/`
- [x] A fresh checkout has every evidence-report artifact link resolve

## Validation

### Import check
```
$ python -c "import sys; sys.path.insert(0,'scripts'); import harness_bridge; print('import OK')"
import OK ✓
```

### Schema compliance
```
$ python scripts/cat_validate.py --all
...
CAT validation passed.
exit: 0 ✓
```

### Link resolution
```
evidence/runs/DEMO-001/
├── cheap_review.md          ✓
├── final_review_opus.md     ✓
├── git_diff_full.txt        ✓
├── git_diff_names.txt       ✓
├── git_diff_stat.txt        ✓
├── review_packet.md         ✓
├── test_output.txt          ✓
├── test_output_attempt1.txt ✓
├── worker_response.md       ✓
└── worker_response_attempt1.md ✓

All 10 artifact links in updated report resolve. ✓
```

### .gitignore verification
- `.agent/runs/` — ignored (transient scratch) ✓
- `evidence/runs/` — NOT ignored (tracked, durable) ✓

## Stop Conditions — None Hit

- ✓ No report orphaned (only BEAD-CAT-002-003 report referenced `.agent/runs/` paths; updated)
- ✓ Bridge change stayed within allowed_paths (`scripts/harness_bridge.py`, `evidence/**`, `.gitignore`)
- ✓ No secrets/credentials in DEMO-001 artifacts (utility functions only: `add`, `is_even`, `slugify`)

## Design Decisions

1. **`copy_durable_artifacts()` copies, not moves** — `.agent/runs/` scratch remains for any in-flight harness tools that still reference it.
2. **Selective copy of 7 named artifact types** — only known-safe files copied; no wildcard to avoid accidentally persisting temp files.
3. **`shutil.copy2`** — preserves timestamps for audit accuracy.
4. **Report updated in-place** — no new report file; existing `BEAD-CAT-002-003_harness_run.md` updated to new paths.

## Handoff

**All BEADs in MP-CAT-002 are now archived.** Mission ready for Human Owner review:
- Transition `MP-CAT-002: approved → dispatched → in_progress → validating → reviewed → closed → learned`
- Human gate required before merge of any DEMO-001 patch to main
