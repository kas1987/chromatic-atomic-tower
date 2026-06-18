# Incident Log

## INC-001

Date: 2026-06-17
Mission: MP-CAT-A007-4C01 (Loghouse Intelligence)
BEAD: BEAD-CAT-A007-4C01-* (active)
Agent: Codex / GitHub Copilot (VS Code extension host)
Trigger: Codex was running a loghouse build loop while mp-cat-006 pytest needed a clean shared tree.
What happened: Codex continued writing files (`scripts/loghouse/`, `tests/test_loghouse_*.py`, `evidence/logs/`) after its VS Code window was closed. Window close does not terminate the Copilot agent — it runs inside the VS Code extension host (`Code.exe`), not as a standalone process. The agent looped for 10+ minutes undetected, stamping evidence reports at ~30-second intervals. A second burst of files landed ~30 seconds after `Stop-Process -Name Code -Force` during shutdown flush.
Files affected: 54 files across `scripts/loghouse/`, `tests/`, `evidence/reports/`, `docs/architecture/`, `schemas/`, `reference/loghouse/`
Immediate containment: `Stop-Process -Name "Code","node" -Force`; wait 30s for shutdown burst; `git add -A && git commit` twice on `mp-cat-007-log-intelligence` to preserve all work.
Recovery recommendation: Before switching branches in a multi-agent session, always confirm the tree is quiet using mtime check: `Get-ChildItem -Recurse | Where-Object LastWriteTime -gt (Get-Date).AddSeconds(-90)`. Do not rely on `git status` or process lists alone.
Learning: See Anti-pattern: Shared tree without agent lock in PATTERN_LIBRARY.md.

---

## Incident template

```md
## Incident ID

Date:
Mission:
BEAD:
Agent:
Trigger:
What happened:
Files affected:
Immediate containment:
Recovery recommendation:
Learning:
```
