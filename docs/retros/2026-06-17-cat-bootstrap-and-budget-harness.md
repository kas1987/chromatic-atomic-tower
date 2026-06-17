# Session Retrospective — CAT bootstrap → budget agent harness MVP

**Date:** 2026-06-17
**Mission:** MP-CAT-000 (Establish Core), MP-CAT-001 (draft promotion), MP-CAT-002 (Multi-Model Coding Harness MVP)
**PRs merged:** #1 (harness MVP + bridge), #2 (VS Code surface), #4 (real ticket `cat_stats.py`). #3 closed (duplicate of #2).
**Final `master`:** `410e6eb` — repo check ✓ · validate --all ✓ · GO ready ✓ · pytest 29/29 ✓

## What shipped
- **CAT Sprint 000 adopted as a live repo** — package promoted to `C:\.01_CAT` root, all gates green, baseline committed (`d0d86b4`) and pushed to GitHub (`kas1987/chromatic-atomic-tower`).
- **Model memory established** — Kimi (`kimi-k2.7-code:cloud`) and MiniMax (`minimax-m3:cloud`) verified via Ollama Cloud; captured to CAT learnings, `bd`, and Claude memory.
- **MP-CAT-001 promotion** drafted by Kimi, schema-gated, staged for human approval (not promoted).
- **MP-CAT-002 budget agent harness MVP** — `.agent/` control layer, `scripts/harness_run.py` (ticket → worker → scoped-diff validation → cheap review → review packet, 2-retry cap, never merges), `scripts/harness_bridge.py` (run → CAT evidence + non-terminal BEAD state).
- **First real ticket through the harness** — worker `kimi-k2.7-code:cloud` generated `scripts/cat_stats.py`; 12/12 tests; merged via PR #4 after independent Opus final review.

## Learnings

### 1. Ollama Cloud tags are non-obvious — read them, don't guess
`kimi-k2.7-code:cloud` (with the dot) and `minimax-m3:cloud` only became known from the Ollama app's model selector; every guessed tag (`kimi-k2:*`, `minimax-m2:*`) 404'd.
**Action:** Always confirm cloud model tags from the app/registry before wiring routes. Drive them via the HTTP API (`stream:false, think:false`), not `ollama run` (TUI escape-code corruption); strip `\r` on Windows.

### 2. Schema-gate model output; never trust the model's self-report
Kimi's first MP-CAT-001 draft had 8 schema violations (invented enums, float-for-int, wrong shapes). A single validator-feedback repair round fixed all 8.
**Action:** Any LLM-authored contract validates against its JSON schema before staging; feed validator errors back for one bounded repair round.

### 3. CI does not run pytest — green CI ≠ tests pass
`.github/workflows/validate-cat.yml` runs `cat_check_repo` + `cat_validate --all` + `cat_resolve_go`, but not `pytest`. PR #4's CI was green while the actual `cat_stats` tests were only verified by me locally.
**Action:** Add a `pytest` step to the workflow (see Follow-up). Until then, verify tests independently before merging code PRs.

### 4. Worker-patch diffs must be scoped, or review gates fire false negatives
The first harness run's cheap review returned REJECT — not from a real problem, but because unscoped `git diff` swept in unrelated working-tree edits and missed the untracked worker file. A `scoped_diff()` (intent-to-add `git add -N` → diff → reset) fixed it; cheap review flipped to APPROVE.
**Action:** Scope evidence diffs to the ticket's allowed files (including untracked) so escalation signal is trustworthy.

### 5. Agent worktree isolation fails on a repo `git init`'d mid-session
The real-ticket subagent couldn't launch with `isolation: worktree` ("not in a git repository"); the harness didn't see the repo created after session start. Re-ran in the main tree (safe, since the parallel agent had finished).
**Action:** For mid-session-initialized repos, don't rely on agent worktree isolation; sequence agents or use the main tree. Manual `git worktree add` still works (used it for read-only PR verification).

### 6. Concurrent human + agent git activity shifts branch state under you
The working tree's checked-out branch changed (`master` → feature → `harness/vscode-integration` → `master`) as the human merged/edited in parallel. A blind `pytest` ran against the wrong branch and found no files.
**Action:** Re-check `git branch --show-current` and `git status` immediately before any working-tree operation; prefer read-only inspection via `origin/<ref>` and PR APIs when the human is active.

## KPI snapshot
| KPI | Value |
|---|---|
| PRs merged | 3 (#1, #2, #4) |
| Harness loop proven on real code | Yes (cat_stats.py, 12/12) |
| Opus calls on worker output | 1 per ticket (final review only) |
| Worker retries used | 0 (passed first attempt both tickets) |
| master validation | repo ✓ / schema ✓ / GO ✓ / pytest 29 ✓ |

## Follow-up
- **Add `pytest` to `.github/workflows/validate-cat.yml`** — close the CI gap from Learning #3 (route as a harness ticket).
- **MP-CAT-001** still `draft` promotion staged — awaits human approval to dispatch the state-transition engine.
- Untracked by design: `scripts/gh_app_token.*`, `.env.example` edit — human to handle (secret-adjacent).
- Pre-existing `bd` P1 items (mc-22w, mc-6a5, …) belong to harness-v2, not CAT — out of scope here.
