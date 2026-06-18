# Opus Final Review — DEMO-001

- Reviewer: Claude Opus 4.8 (final_reviewer role, MP-CAT-002)
- Date: 2026-06-17
- Worker: kimi-k2.7-code:cloud (1/2 attempts)

## Decision: APPROVE (patch) + REQUEST_REVISION (harness runner)

### Patch verdict: APPROVE
The worker deliverable `scripts/harness_demo.py` is correct, minimal, and stdlib-only.
Independently re-ran `python -m pytest -q tests/test_harness_demo.py` → **14 passed**.
`git status` confirms the worker created exactly one file (`scripts/harness_demo.py`,
untracked); no out-of-scope modifications, no imports, no guardrail violations.
Acceptance criteria fully met. Merge remains gated on Human Owner approval (not granted here).

### Harness verdict: REQUEST_REVISION (runner defect, not the patch)
The cheap reviewer (minimax-m3:cloud) returned REJECT for the WRONG reason — a false
negative caused by a diff-scoping bug in `scripts/harness_run.py`:
- It runs unscoped `git diff`, which captured pre-existing uncommitted working-tree edits
  (`learnings/*`, `missions/registry/MISSION_REGISTRY.yaml`) unrelated to the ticket.
- The worker's actual file is untracked, so it did not appear in `git diff` at all —
  the reviewer saw "4 unrelated files changed, implementation file missing" and rejected.

Required revision before the next ticket:
1. Scope the evidence diff to the ticket's allowed files only, e.g.
   `git diff HEAD -- <allowed>` plus `git diff --no-index /dev/null <new_untracked_allowed>`
   (or `git add -N` the allowed new files then diff), so the packet shows the worker's
   real contribution and nothing else.
2. Re-run the cheap review on the scoped diff so escalation signal is trustworthy.

## Resolution (2026-06-17, runner fix verified)
The diff-scoping defect is FIXED in `scripts/harness_run.py`: a new `scoped_diff()` helper
diffs only the worker's written files (intent-to-add → diff → reset, leaving the repo
pristine), including untracked new files and excluding unrelated working-tree edits. Wired
into the validation, review-packet, and cheap-review sites. DEMO-001 re-run:
- Files Changed (scoped): `scripts/harness_demo.py` only — 1 file, 16 insertions.
- Cheap reviewer (minimax-m3:cloud): **APPROVE**, "No scope drift" — false negative resolved.
- `git status` confirms `scripts/harness_demo.py` remains untracked (intent-to-add reset; nothing staged).
Patch APPROVE stands; harness REQUEST_REVISION is now CLEARED.

## Net result
MP-CAT-002 MVP loop works end to end: ticket → worker (Kimi) → file written within scope →
tests run (14/14) → cheap review → packet assembled → escalated for final review. One real
runner bug found by the review gate doing its job (even if for the wrong stated reason).
