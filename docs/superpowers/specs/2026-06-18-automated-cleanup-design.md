# Automated Cleanup — Design Spec
**Date:** 2026-06-18
**Status:** Approved

## Overview

A single orchestrator script (`scripts/cat_cleanup.py`) runs four cleanup phases against the CAT repo. It operates in `--dry-run` mode by default and `--execute` mode for live runs. A weekly CI workflow calls it with `--execute --all`; humans call it via `make cleanup` or `make cleanup-run`.

---

## Architecture

### New files

| File | Purpose |
|------|---------|
| `scripts/cat_cleanup.py` | Orchestrator + all four phase runners |
| `.github/workflows/cat-cleanup.yml` | Scheduled + manual-dispatch CI job |

### Makefile additions

```makefile
.PHONY: cleanup cleanup-run

cleanup:
	python scripts/cat_cleanup.py --dry-run --all

cleanup-run:
	python scripts/cat_cleanup.py --execute --all
```

### CLI interface

```
python scripts/cat_cleanup.py [--dry-run] [--execute] [--phases PHASE ...] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | yes | Report what would change, touch nothing |
| `--execute` | no | Apply all deletions |
| `--phases` | all | Space-separated subset: `branches worktrees artifacts cache` |
| `--json` | no | Emit structured JSON to stdout (for CI consumption) |
| `--include-venv` | no | Also delete `.venv/` in cache phase (opt-in) |

### Data model

```python
@dataclass
class CleanupResult:
    phase: str
    found: list[str]
    deleted: list[str]
    skipped: list[str]
    flagged: list[str]
    errors: list[str]

@dataclass
class CleanupReport:
    mode: str          # "dry-run" | "execute"
    phases: list[CleanupResult]
    timestamp: str
```

Report written to `evidence/tower/cleanup_report.md` on every run. `--json` additionally emits the report as JSON to stdout.

---

## Phase 1: Branches

### Classification rules (evaluated in order)

| Rule | Condition | Action |
|------|-----------|--------|
| Protected | Name in `{"master", "main"}` | Never touch |
| Open PR | Branch has an open GitHub PR | Skip, log |
| Merged | 0 commits ahead of `origin/master` | **Delete** local + remote |
| Auto-generated, no PR | Prefix in `("worktree-agent-", "claude/")`, no open PR | **Delete** remote only |
| Unmerged, no PR | All other prefixes, ahead of master, no open PR | **Flag** — report only, no deletion |

### Constants (in `cat_cleanup.py`)

```python
AUTO_PREFIXES = ("worktree-agent-", "claude/")
PROTECTED = {"master", "main"}
```

### Implementation notes

- **Merge check:** `git rev-list --count origin/master..<branch>` == 0
- **PR check:** single `gh pr list --state open --json headRefName` call → build a `set` to avoid N+1 API calls
- **Local deletion:** `git branch -d <branch>` (safe) or `git branch -D` for auto-prefixed branches
- **Remote deletion:** `gh api repos/<owner>/<repo>/git/refs/heads/<branch> -X DELETE`

---

## Phase 2: Worktrees

Parses `git worktree list --porcelain`. Excludes the main worktree (first entry).

| Condition | Action |
|-----------|--------|
| Branch deleted on remote | **Remove** (`git worktree remove --force <path>`) |
| Branch merged into master | **Remove** |
| Uncommitted changes present | Skip, log warning |
| Anything else | Skip |

After all removals, runs `git worktree prune` to clear stale admin refs.

---

## Phase 3: Artifacts

Targeted deletions matching `.gitignore` entries — nothing untracked is removed.

| Target | Rule |
|--------|------|
| `.agent/runs/<dir>/` | Delete all subdirs; preserve `.gitkeep` |
| `evidence/reports/*CLOSEOUT-EXAMPLE*` | Delete (test-generated) |
| `evidence/reports/*DOES-NOT-MATCH*` | Delete (test-generated) |
| `*.worktree/` dirs under repo root | Delete orphaned checkout dirs |

---

## Phase 4: Cache

| Target | Rule |
|--------|------|
| `**/__pycache__/` | Delete all (recursive) |
| `.pytest_cache/` | Delete |
| `pytest-cache-files-*/` | Delete |
| `.coverage`, `coverage.xml`, `htmlcov/` | Delete |
| `.venv/` | Skip unless `--include-venv` passed |

---

## CI Workflow: `cat-cleanup.yml`

### Triggers

```yaml
on:
  schedule:
    - cron: '0 3 * * 1'   # Monday 03:00 UTC
  workflow_dispatch:        # manual trigger from GitHub UI
```

### Job steps

1. Checkout master with `fetch-depth: 0` (full history for merge checks)
2. Set up Python, install `requirements.txt`
3. Run `python scripts/cat_cleanup.py --execute --all --json`
4. If disk files were deleted → `git add -A && git commit -m "chore(cleanup): automated sweep <date>" && git push`
5. Upload `evidence/tower/cleanup_report.md` as artifact (30-day retention)

### Permissions required

`GH_TOKEN` (already in repo secrets) with `contents: write` and `pull-requests: read`.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Clean — nothing found or everything cleaned |
| `1` | Script error (exception, bad args) |
| `2` | Dry-run found items (non-zero would-delete count) |

---

## Dry-run output format

```
=== CAT Cleanup Report (dry-run) ===

[branches]  4 would delete, 1 flagged, 1 skipped
  DELETE  chore/root-cleanup (merged)
  DELETE  fix/test-isolation-health-2026-06-17 (merged)
  DELETE  worktree-agent-a2d4e1846619a47c2 (auto, no PR)
  DELETE  claude/test-coverage-analysis-8yv1j7 (auto, no PR)
  FLAG    feat/my-wip (3 commits ahead, no PR)
  SKIP    mp-cat-a014-toolplanes (open PR #41)

[worktrees]  1 would remove
  REMOVE  C:\.worktrees\agent-abc123 (branch deleted)

[artifacts]  34 files would delete
  DELETE  .agent/runs/CI-001/ (10 files)
  DELETE  evidence/reports/*CLOSEOUT-EXAMPLE* (3 files)

[cache]  127 files would delete
  DELETE  __pycache__/ (12 dirs, 112 files)
  DELETE  .pytest_cache/ (15 files)

Summary: 4 branches, 1 worktree, 161 files — 0 deleted (dry-run)
```

---

## Out of scope

- Stale GitHub Issues cleanup
- Dependabot / security alert management
- Secrets rotation
- `.venv/` deletion (opt-in via `--include-venv`, not run by default CI)
