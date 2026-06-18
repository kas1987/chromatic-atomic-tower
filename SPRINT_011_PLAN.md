# Sprint 011 Plan — Agent Scorecard Automation

**Mission:** MP-CAT-A011-4C01  
**Sprint ID:** SPRINT-011  
**State:** sprint_active  
**Tower State:** TOWER-STATE-011  
**Started:** 2026-06-18  

---

## Objective

Automate agent trust scorecard maintenance: define a validated schema, build a
CLI scoring engine, add tool-budget usage tracking, and wire scorecard updates
into the BEAD closeout flow.

## Prerequisites

- [x] MP-CAT-A009-4C01 closed
- [x] MP-CAT-A010-4C01 closed (PR #26 merged)
- [x] Tower is sprint_idle on master
- [x] Human Owner GO signal received

---

## BEADs

| BEAD | Title | Status | Agent Role |
|------|-------|--------|------------|
| BEAD-CAT-A011-4C01-01 | Define agent scorecard schema and upgrade data model | active | Architect |
| BEAD-CAT-A011-4C01-02 | Implement trust scoring engine CLI | queued | Builder |
| BEAD-CAT-A011-4C01-03 | Implement tool-budget tracker | queued | Builder |
| BEAD-CAT-A011-4C01-04 | Wire scorecard into bead closeout and produce final evidence | queued | Builder |

---

## Acceptance Criteria

- `schemas/agent_scorecard.schema.json` created and validates via `cat_validate.py`.
- `agents/registry/AGENT_SCORECARD.yaml` upgraded to v1.0.0 with history list.
- `scripts/cat_agent_scorecard.py` implements: `score-bead`, `promote`, `demote`, `penalize`, `report`.
- `scripts/cat_tool_budget_tracker.py` implements: `summarize`, `check`.
- Bead closeout calls `score-bead` in dry-run by default.
- `docs/agent_scorecard_spec.md` written.
- All tests pass (230+ expected).
- Evidence reports produced for each BEAD.

---

## Scoring Formula

| Event | Delta |
|-------|-------|
| BEAD completed | +5 |
| BEAD failed | -10 |
| Incident penalty | -15 |
| Floor (severe) | 40 |
| Promote threshold | ≥ 85 → trusted |
| Demote threshold | ≤ 55 → restricted |

---

## Constraints

- No automatic trust-level changes — human gate required before any write.
- `--dry-run` is the default for all mutation subcommands.
- No mutation outside `allowed_paths` defined per BEAD.

---

## Validation Chain

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_align_check.py --strict
python -m pytest tests/ -q
```

---

## Evidence Directory

`evidence/scorecard/`
