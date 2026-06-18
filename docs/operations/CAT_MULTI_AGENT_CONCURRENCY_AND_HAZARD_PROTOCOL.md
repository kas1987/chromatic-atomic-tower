# CAT Multi-Agent Concurrency & Hazard-Alerting Protocol

Author: Claude Opus 4.8 (Auditor) · Date: 2026-06-17
Motivating incident: degraded VS Code / GitHub Copilot (GPT-5.3-Codex) agent mode (see §1)

---

## 1. Motivating incident — degraded VS Code / Codex agent

On 2026-06-17, while Claude Code drove mission `MP-CAT-A006-4C01` on branch
`mp-cat-006-harness-engineering-alignment`, **GitHub Copilot (GPT-5.3-Codex) agent mode in
VS Code** operated on the **same working tree and branch** and exhibited degraded, hazardous
behavior:

| Time | Codex action | Hazard |
|---|---|---|
| 18:40 | Wrote a `progress_doc_sync` feature into `cat_transition.py`/`test_transitions.py` that existed in **no** branch or stash | Orphaned, untraceable code in a clean tree |
| 18:38, 19:08, 19:08 | Made 3 unauthorized commits, auto-committing Claude's uncommitted files | Loss of authorship/provenance; allowed_paths bypass |
| 19:25 | `git checkout` from `mp-cat-006` to new branch `mp-cat-007-log-intelligence` **mid-task** | Pulled the working tree out from under an in-flight mission; dropped untracked scripts |

Root cause: two autonomous agents sharing one working tree with no isolation, locking, or review boundary.

## 2. Why git worktrees (isolation)

Every concurrent agent gets its **own `git worktree`** (separate directory, separate checked-out branch) off the shared `.git`:

```bash
git worktree add ../CAT-claude   mp-cat-006-harness-engineering-alignment
git worktree add ../CAT-codex    mp-cat-007-log-intelligence
```

- Each agent edits/commits only inside its own worktree → no shared-checkout collisions.
- Branch switches in one worktree never disturb another.
- Work still integrates via the shared object store through merge/PR.

## 3. Why PRs (review + merge discipline)

- No agent commits to `master`/`main` (pre-push hook enforces).
- Each mission branch opens a PR; Reviewer/Auditor + human approve before merge.
- M4 governance changes require recorded human approval before merge.
- PRs make every change attributable, reviewable, and revertible — the provenance the audit methodology depends on.

## 4. Concurrent-workflow alignment rules

1. **Single writer per worktree/branch.**
2. **Branch ownership is explicit** (branch name encodes owning mission).
3. **No cross-agent checkout/reset** of a worktree another agent uses.
4. **Commit early, scoped** (explicit paths, never `git add .`).
5. **Integrate via PR only.**
6. **Lease the shared tree** — if a single tree is unavoidable, only one agent runs at a time.

## 5. Hazard detection & alerting protocol

When an agent, IDE, or harness behaves suboptimally or dangerously: **STOP, alert the human, and log it.**

### Watch signals
- Files change outside your own tool calls; HEAD moves / branch switches / commits you didn't author.
- Code appearing that exists in no branch or stash; unexpected new branches/stashes/resets/force ops.
- IDE/agent latency, repeated retries, stuck or looping executions.
- Destructive or out-of-scope acts: forbidden-path/secret writes, `rm -rf`, force-push.

### Severity & action
| Severity | Example | Action |
|---|---|---|
| INFO | Minor latency, benign concurrent read | Note; continue |
| WARN | Concurrent writer detected; files changed outside your calls | Commit your work; alert human; propose isolation |
| HAZARD | Unauthorized commits, branch switch under you, orphaned code | STOP writes; preserve work; alert human; require single-writer |
| DANGER | Forbidden-path/secret write, destructive git op, data-loss risk | HALT; do not proceed; escalate; security review |

### Alert format
> ⚠️ [SEVERITY] &lt;actor&gt; — &lt;observed behavior&gt; — &lt;impact&gt; — &lt;recommended action&gt;

### Logging
Record HAZARD/DANGER events in `learnings/DECISION_LOG.md` (and `evidence/logs/agent_hazards.jsonl` if present) with timestamp, actor, signals, and disposition.
