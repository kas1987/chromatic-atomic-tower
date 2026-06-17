# Session Retrospective — Multi-Model Eval, Governance Reconciliation & Merge Automation

**Date:** 2026-06-17
**PRs merged:** #16 (retro), #17 (PR-14 state-machine fixes), #18 (governance), #19 (merge script), #20 (transition engine), #21 (engine retro)
**Epics:** MP-CAT-001 — BEAD-CAT-001-001 (rules) + BEAD-CAT-001-002 (`cat_transition.py`) landed on master

> Engine internals are covered in `2026-06-17-cat-001-transition-engine.md`. This retro covers the
> governance reconciliation, the merge automation, the Kimi performance trial, and the harness research.

## What shipped
- **Operator-plane exemption codified** (`CAT_MANIFEST` §6.1 + `AGENTS.md`, #18): human-invoked meta-work (closeouts, retros, kickoffs, hygiene) is exempt from BEAD `allowed_paths`, logged in `DECISION_LOG`, still bound by `forbidden_paths`. Ended a bot P1 that recurred on PR #10 and #16.
- **Transition-log path reconciled** to `evidence/logs/transitions.jsonl` across `STATE_MACHINE.md`, BEAD-CAT-001-002 `allowed_paths`, and the MP-CAT-001 mission (#18) — unblocked the engine.
- **`scripts/cat_merge_ready.py`** (#19): deterministic, no-LLM ready-PR merger (dry-run default, `--execute`, `--update-behind`).
- **Kimi performance trial** (`kimi-k2.7-code:cloud`): implementation (`cat_transition.py` draft) + orchestration (merge plan), both evaluated in a sandbox.
- **Deep-research report** on local/Ollama coding-agent harnesses (21 sources, 25 verified claims): identified "Pi" and recommended a pattern to imitate.
- **Merged all open PRs** and confirmed the engine is on master.

## Learnings

### 1. Sandbox-evaluate model output before trusting it
Kimi's `cat_transition.py` passed every functional check in an isolated sandbox — except it reserialized the registry via `yaml.safe_dump` (quote/indent change, **comment loss**). It *looked* perfect.
**Action:** Always run model-generated code in an isolated repo copy against the real DoD; appearance ≠ correctness. Treat whole-file YAML reserialization as a defect for governance files.

### 2. Match the tool to the task — don't LLM a mechanical job
Kimi is a tool-less code worker; PR merging is pure `gh`/`git` orchestration. The right tool was a **deterministic script**, not a model.
**Action:** Reserve LLMs for judgement (review responses, code gen); automate mechanical git ops with scripts.

### 3. Local models stop egress, not command execution
Verified (NVIDIA, 3-0): agents run with full user privileges, so **OS-level sandboxing is required regardless of harness**; "just block egress" was refuted (0-3) as a complete defense. Config-file prompt injection is the *primary* threat.
**Action:** Sandbox any command-executing worker; treat `.github/chatmodes/*` + `prompts/*` as a trust surface; pin the unpinned `npx -y` MCP servers in `.vscode/mcp.json`.

### 4. "Pi" identified; pick the gated pattern
"Pi" = `earendil-works/pi` — Ollama-runnable but **no permission system / no sandbox → too weak** for governance (matches the owner's instinct). Continue.dev's **per-role local-Ollama routing** is the pattern to imitate; Cline is more capable but exploit-prone (`.clinerules` injection, bypassable approval, CVEs patched ≥3.35.0).

### 5. CLI tests must isolate from the live registry
The merged transition-engine suite goes **red on master** (13 failures) because it asserts `--from queued` for a BEAD the live WIP already advanced past — the tests run against the working-tree registry, not a fixture.
**Action:** Engine/transition tests must build an isolated fixture registry in a tmp dir.

### 6. Don't-ask-for-git feedback
Owner recorded: never ask before committing/pushing/opening PRs — just do it (still use branch+PR; master push is hook-blocked).

## KPI snapshot
| KPI | Value |
|---|---|
| PRs merged this segment | 6 (#16–#21) |
| Open PRs | 0 |
| Sprint 001 engine (`cat_transition.py`) | on master |
| Kimi trial | impl functional (1 YAML flaw); orchestration solid |
| Deep-research | 21 sources, 25 verified, 5 killed |
| master `cat_validate` | PASS |
| master `cat_check_repo` | FAIL (2 stray `temp_*.txt`) |
| master `pytest` | 46 pass / 15 fail (13 transition + 2 guard-via-temps) |

## Follow-up
- **Fix 13 `test_transitions.py` failures** — isolate the suite from the live registry (use a tmp fixture).
- **Remove `temp_cat_002_validate.txt` + `temp_validate.txt`** from root (the stray-root guard is correctly failing on them) — left in place; they're not mine.
- **Harden Kimi's pattern** if accepting model-written mutators: require minimal/surgical YAML edits, not `safe_dump` reserialization.
- **VS Code worker** — imitate Continue.dev per-role Ollama routing; run inside an OS sandbox; pin MCP server versions.
- Use the now-merged `cat_transition.py` to replace manual operator status transitions going forward.
