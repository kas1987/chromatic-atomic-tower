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
