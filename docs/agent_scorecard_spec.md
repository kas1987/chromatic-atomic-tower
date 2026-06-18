# Agent Scorecard Specification

**Version:** 1.0.0  
**Mission:** MP-CAT-A011-4C01  
**Status:** active  

---

## Overview

The CAT Agent Scorecard is a machine-readable trust ledger that tracks each agent
role's delivery history. Scores drive visibility into agent reliability — they do
**not** automatically change any agent's permissions. All trust-level changes
(`trusted` / `restricted`) require explicit `--execute` and Human Owner approval.

---

## Data Model

File: `agents/registry/AGENT_SCORECARD.yaml`  
Schema: `schemas/agent_scorecard.schema.json`

```yaml
version: 1.0.0
last_updated: '<ISO timestamp>'
score_policy:
  starting_score: 70
  promote_threshold: 85
  demote_threshold: 55
  severe_incident_cap: 40
agents:
  - role: Builder
    score: 70.0
    completed_beads: 0
    failed_beads: 0
    incidents: 0
    current_trust: provisional
    history: []
```

### Trust Levels

| Level | Score Range | Meaning |
|-------|-------------|---------|
| `provisional` | > 55, < 85 | Default for new agents |
| `trusted` | ≥ 85 | Sustained delivery record; requires human approval to set |
| `restricted` | ≤ 55 | Multiple failures or incidents; requires human approval to set |

### History Entry Schema

Each history entry records one scoring event:

```yaml
- timestamp: '2026-06-18T06:00:00+00:00'
  event: bead_completed        # bead_completed | bead_failed | incident | promotion | demotion
  delta: 5
  bead_id: BEAD-CAT-A011-4C01-01
  note: ''                     # optional
```

---

## Scoring Formula

| Event | Score Delta | Notes |
|-------|-------------|-------|
| `bead_completed` | +5 | BEAD status = completed |
| `bead_failed` | -10 | BEAD status = failed |
| `incident` | -15 | Triggered by `penalize` subcommand |
| Floor | 40 | Minimum score regardless of penalties (`severe_incident_cap`) |
| Ceiling | 100 | Maximum score |

### Promotion / Demotion Thresholds

- **Promote** → `trusted`: score ≥ 85 (`promote_threshold`)
- **Demote** → `restricted`: score ≤ 55 (`demote_threshold`)

Both transitions require `--execute` AND human review.

---

## CLI Reference (`scripts/cat_agent_scorecard.py`)

### score-bead

Record a BEAD outcome for an agent role.

```bash
python scripts/cat_agent_scorecard.py [--dry-run | --execute] score-bead \
    --role Builder \
    --bead BEAD-CAT-A011-4C01-01 \
    --result completed
```

| Flag | Values |
|------|--------|
| `--result` | `completed` (+5) or `failed` (-10) |
| `--dry-run` | Print proposed change (default) |
| `--execute` | Write to AGENT_SCORECARD.yaml |

### penalize

Apply an incident penalty (-15, floor 40).

```bash
python scripts/cat_agent_scorecard.py --execute penalize \
    --role Builder \
    --bead BEAD-CAT-A011-4C01-01 \
    --note "Touched forbidden path"
```

### promote / demote

Change trust level. Score must meet threshold; requires `--execute` and human approval.

```bash
python scripts/cat_agent_scorecard.py --execute promote \
    --role Builder \
    --bead BEAD-CAT-A011-4C01-01

python scripts/cat_agent_scorecard.py --execute demote \
    --role Builder \
    --bead BEAD-CAT-A011-4C01-01
```

### report

Print per-agent summary.

```bash
python scripts/cat_agent_scorecard.py report [--role Builder] [--json]
```

---

## Tool-Budget Tracker CLI (`scripts/cat_tool_budget_tracker.py`)

Compares actual tool usage against a BEAD contract's `tool_budget` field.

### summarize

```bash
python scripts/cat_tool_budget_tracker.py summarize \
    --bead beads/active/BEAD-CAT-A011-4C01-01.yaml \
    --actual evidence/scorecard/actual_usage.json \
    --output evidence/scorecard/BEAD-CAT-A011-4C01-01_budget.json
```

### check

Exits 1 if any budget category is exceeded; exits 0 otherwise.

```bash
python scripts/cat_tool_budget_tracker.py check \
    --bead beads/active/BEAD-CAT-A011-4C01-01.yaml \
    --actual evidence/scorecard/actual_usage.json
```

#### Actual Usage JSON Format

```json
{"search": 1, "read": 5, "write": 3, "execute": 2}
```

If `--actual` is omitted, all usage is treated as 0 (check always passes).

---

## Closeout Integration

`cat_sprint_closeout.py` calls `score-bead` for each BEAD in the closing mission.
The call uses `--execute` (no dry-run) so scores update automatically at closeout.

To disable: remove or skip the `_score_beads_on_closeout` call in `cat_sprint_closeout.py`.

---

## Increment Files

Each `--execute` call to `score-bead` writes a per-BEAD increment file to:

```
agents/scorecards/{BEAD_ID}_{role}_{event}.yaml
```

These files are lightweight audit records for individual scoring events.

---

## Security Constraints

- Scoring does NOT mutate `agents/registry/AGENT_REGISTRY.yaml`.
- No agent role changes (can_dispatch, autonomy_level) are permitted by this system.
- All trust-level changes require `--execute` AND are logged to `history`.
- The scorecard cannot be written without an explicit bead_id reference.
