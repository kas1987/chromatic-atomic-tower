# Evidence Report: MP-CAT-002 T003 — First Harness Run

**Date:** 2026-06-17
**Mission:** MP-CAT-002 (Multi-Model Coding Harness MVP)
**BEAD:** BEAD-CAT-002-003 (Run first local worker patch)
**Reporter:** Builder subagent

---

## 1. Ticket

**ID:** DEMO-001
**Title:** Implement harness_demo.py utility functions
**Objective:** Create `scripts/harness_demo.py` with `add`, `is_even`, `slugify` functions so all tests in `tests/test_harness_demo.py` pass.
**Allowed Files:** `scripts/harness_demo.py` only
**Test Command:** `python -m pytest -q tests/test_harness_demo.py`

---

## 2. Worker Run

| Field | Value |
|---|---|
| Worker model | `kimi-k2.7-code:cloud` |
| Reviewer model | `minimax-m3:cloud` |
| Endpoint | `http://localhost:11434` |
| Attempts used | 1 / 2 |
| Files written by worker | `scripts/harness_demo.py` |
| Guardrail violations | None |
| Escalation notes | None |

---

## 3. Test Results

### Baseline (before worker run)

```
ERROR collecting tests/test_harness_demo.py
ModuleNotFoundError: No module named 'scripts.harness_demo'
1 error in 0.21s
```

### After worker run (Attempt 1 — PASSED)

```
..............                                                           [100%]
14 passed in 0.03s
```

All 14 tests passed on the first worker attempt. No retry was required.

---

## 4. Worker-Generated Implementation

`scripts/harness_demo.py` (17 lines, stdlib only):

```python
"""Utility functions for the harness demo ticket."""

def add(a, b):
    """Return the arithmetic sum of a and b."""
    return a + b

def is_even(n):
    """Return True if n is even, False otherwise."""
    return n % 2 == 0

def slugify(s):
    """Lowercase, strip, and collapse internal whitespace to single hyphens."""
    return "-".join(s.lower().strip().split())
```

---

## 5. Cheap Reviewer Notes (minimax-m3:cloud)

**Decision:** REJECT (with important context below)

The reviewer correctly noted that `git diff` showed 4 files outside the allowed list
(`learnings/DECISION_LOG.md`, `learnings/ECHO_LOG.md`, `learnings/PATTERN_LIBRARY.md`,
`missions/registry/MISSION_REGISTRY.yaml`) in the diff. These changes were **pre-existing
uncommitted changes from earlier in the session** — not written by the worker. The worker
itself only wrote `scripts/harness_demo.py` (confirmed by parse output and the allowed-files
guardrail in `harness_run.py`).

This is a known limitation of using `git diff` (unstaged working tree) as the scope check
when pre-existing dirty files exist. A future improvement would scope the diff to only
the files listed in the ticket's Allowed Files (e.g., `git diff -- scripts/harness_demo.py`).

The reviewer's REJECT is technically correct per the evidence presented; the root cause is
the diff-scope ambiguity, not an actual worker scope violation.

---

## 6. Governance Checks

| Check | Result |
|---|---|
| `python scripts/cat_check_repo.py` | PASS — 19 required files, 14 required directories checked |
| `python scripts/cat_validate.py --all` | PASS — all missions and beads valid (CAT validation passed) |

No governed files were touched by the harness implementation.

---

## 7. Guardrail/Escalation Notes

- **Guardrail violations:** 0 (the worker respected the allowed-files constraint)
- **Escalation triggered:** No
- **Scope drift by worker:** None confirmed — the `is_allowed_path` check in `harness_run.py` skipped any non-allowed FILE blocks; the pre-existing dirty working tree caused `git diff` to show other files
- **Known issue logged:** The cheap reviewer's REJECT was driven by `git diff` including pre-existing
  uncommitted changes outside the ticket scope. Recommend: future tickets should use
  `git diff HEAD -- <allowed_file_list>` to isolate worker-caused changes.

---

## 8. Artifact Paths

| Artifact | Path |
|---|---|
| Ticket | `.agent/tickets/DEMO-001.md` |
| Worker response | `.agent/runs/DEMO-001/worker_response.md` |
| Test output | `.agent/runs/DEMO-001/test_output.txt` |
| Cheap review | `.agent/runs/DEMO-001/cheap_review.md` |
| Review packet | `.agent/runs/DEMO-001/review_packet.md` |
| Git diff (full) | `.agent/runs/DEMO-001/git_diff_full.txt` |
| Git diff stat | `.agent/runs/DEMO-001/git_diff_stat.txt` |
| Evidence report | `evidence/reports/mp_cat_002_t003_run.md` |

---

## 9. Queue State

`DEMO-001` status advanced to `review` in `.agent/queue.json`.
Status NOT set to `done` — final review and human approval are out of scope for the runner.

---

## 10. Summary

The MP-CAT-002 T003 harness run succeeded:
- Worker model `kimi-k2.7-code:cloud` implemented `scripts/harness_demo.py` in 1 attempt.
- All 14 pytest assertions passed.
- No guardrail violations were triggered by the worker.
- Cheap reviewer flagged pre-existing dirty-tree diff (not a worker violation).
- Governance contracts (cat_check_repo, cat_validate) remain fully valid.
- Review packet is ready for human/Opus final review at `.agent/runs/DEMO-001/review_packet.md`.
