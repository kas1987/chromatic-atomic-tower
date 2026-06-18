# Pattern Library

## Pattern: Donor not foundation

When replacing a legacy Harness, use it as source material but start from a clean architecture.

## Pattern: BEAD-first execution

Agents perform better when the unit of work is atomic, bounded, and validated.

## Pattern: Evidence before closeout

Require proof artifacts before work is declared complete.

## Anti-pattern: Documentation as permission

Long prose can mislead agents. Operational permission belongs in validated contracts.

## Pattern: mtime-watch before branch switch

Before `git checkout` in a multi-agent session, confirm the working tree is truly quiet:
```powershell
Get-ChildItem -Recurse | Where-Object { $_.LastWriteTime -gt (Get-Date).AddSeconds(-90) }
```
Empty output = safe to switch. `git status` and process lists are insufficient — a looping agent
may write only to evidence/logs without touching tracked source files.

## Anti-pattern: Shared tree without agent lock

Running two agents (e.g. Claude Code + Copilot) against the same working tree with no
coordination gate causes pytest failures, dirty checkouts, and silent data loss. Neither agent
knows the other is writing. Mitigations: (1) one agent at a time on a branch, (2) mtime-watch
before any branch op, (3) WIP commit before handing off.

## Pattern: WIP-commit-then-handoff

When stopping one agent's work to switch branches, always `git add -A && git commit -m "wip(...)"` first.
This preserves in-flight state on the correct branch and makes the working tree clean for checkout.
Expect a second commit may be needed if the agent flushes during shutdown.

## Pattern: Dual-agent parallel status review

Two Sonnet agents spawned in parallel — one for working-tree state, one for repo/project structure — complete a full orientation audit in ~2 minutes. More reliable than a single agent because each investigates independently and findings can be cross-checked. Use at session start when the state plane may be stale.

## Anti-pattern: Mission lifecycle skipped at BEAD activation

If BEAD-001 is activated without first transitioning the mission through `approved → dispatched`, the mission gets permanently stuck: when all BEADs eventually complete, the `active_bead_present` guard on `approved → dispatched` can never be satisfied. Always dispatch the mission at the same moment BEAD-001 is activated.

## Anti-pattern: Trusting session-start branch snapshot

The `gitStatus` snapshot injected at session start reflects branch state at conversation open time, not at tool-call time. Concurrent writers (Codex, VS Code) can switch the working branch between snapshot capture and your first commit. Always verify `git branch --show-current` before any commit that depends on being on a specific branch.
