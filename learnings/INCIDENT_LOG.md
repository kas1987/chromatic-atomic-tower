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

## INC-002

Date: 2026-06-18  
Mission: MP-CAT-005  
BEAD: BEAD-CAT-005-002 through 005-005  
Agent: Claude Code (Sonnet 4.6)  
Trigger: Every BEAD closeout transition left `TOWER_STATE.yaml` in schema-invalid state.  
What happened: `cat_transition.py` line 233 set `tower['active_bead_id'] = None`. Python `None` serialises to YAML `null`, but `tower_state.schema.json` declares `active_bead_id` as `type: string`. Every BEAD moved to `completed/failed/archived` silently broke `cat_validate.py --all`.  
Files affected: `state/TOWER_STATE.yaml` (invalid after each transition), `scripts/cat_transition.py` (root cause)  
Immediate containment: Manually patched `active_bead_id` to `""` after each transition during the session.  
Recovery recommendation: Fixed in commit `9b52adf` — line 233 now emits `''`. Also audit other tower-state key assignments for the same `None` pattern.  
Learning: Schema validation should be run as a post-write assertion inside the transition engine itself, not only by the external `cat_validate.py` caller.

---

## INC-003

Date: 2026-06-18
Mission: test/coverage-80pct (PR #45)
BEAD: N/A (test-only spike)
Agent: Claude Code (Sonnet 4.6)
Trigger: Extended test `test_record_writes_and_prints` used a mixed import strategy — `import cat_score_agent as csa` (to monkeypatch) + `from scripts.cat_score_agent import main` (to call) — creating two distinct `sys.modules` entries for the same source file.
What happened: `monkeypatch.setattr(csa, 'SCORECARD_PATH', tmp_path/...)` patched the `cat_score_agent` namespace. But `main()` was imported from `scripts.cat_score_agent` and read its globals from that separate namespace, where `SCORECARD_PATH` was still the real path. On every pytest run, `TestRole` was written to `agents/registry/AGENT_SCORECARD.yaml`, causing `scorecard_parity` to fail for all tests that ran after it — 5 CI failures on PR #45.
Files affected: `agents/registry/AGENT_SCORECARD.yaml` (corrupted per run), `agents/scorecards/BEAD-TEST-001_TestRole_bead_completed.yaml` (stray artefact).
Immediate containment: `git checkout -- agents/registry/AGENT_SCORECARD.yaml`; delete stray scorecard yaml; fix test to call `csa.main()` instead of `main()`.
Recovery recommendation: Never mix `import mod` with `from scripts.mod import func` in the same test file. Use a single namespace exclusively.
Learning: See Anti-pattern: Dual-module import namespace in PATTERN_LIBRARY.md.

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
