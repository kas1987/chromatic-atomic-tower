# CAT Agent Scorecards

## Overview

`scripts/cat_score_agent.py` records agent execution quality events into:

- `agents/registry/AGENT_SCORECARD.yaml` — the canonical per-role score registry
- `agents/scorecards/<BEAD-ID>_<Role>_<event>.yaml` — per-bead event entries

## Scorecard Schema

`schemas/agent_scorecard.schema.json` defines the structure of `AGENT_SCORECARD.yaml`:

```yaml
version: 1.0.0
last_updated: '2026-06-18T16:00:00+00:00'
score_policy:
  starting_score: 70
  promote_threshold: 85
  demote_threshold: 55
  severe_incident_cap: 40
agents:
  - role: Builder
    score: 85
    completed_beads: 5
    failed_beads: 0
    incidents: 0
    current_trust: trusted
    history:
      - timestamp: '2026-06-18T16:00:00+00:00'
        event: bead_completed
        delta: 5
        bead_id: BEAD-CAT-A014-4C01-06
```

## Score Policy

| Event | Delta |
|---|---|
| `bead_completed` | +5 |
| `bead_failed` | -10 (−15 if validation also failed) |
| `incident` | -15 |
| Additional incidents (count > 0) | −5 per incident |

Score is clamped to [0, 100].

## Trust Levels

| Score | Trust |
|---|---|
| ≥ 85 (`promote_threshold`) | `trusted` |
| ≤ 55 (`demote_threshold`) | `restricted` |
| Otherwise | `provisional` |

## Commands

### Preview a mutation (dry-run)

```bash
python scripts/cat_score_agent.py --dry-run --sample
```

Uses a built-in sample event to preview a mutation without writing any files.

```bash
python scripts/cat_score_agent.py --dry-run \
  --role Builder \
  --bead-id BEAD-CAT-A014-4C01-06 \
  --mission-id MP-CAT-A014-4C01 \
  --event bead_completed
```

### Record a real event

```bash
python scripts/cat_score_agent.py --record \
  --role Builder \
  --bead-id BEAD-CAT-A014-4C01-06 \
  --mission-id MP-CAT-A014-4C01 \
  --event bead_completed \
  --budget-used 3
```

Writes to `AGENT_SCORECARD.yaml` and creates a per-bead scorecard entry in `agents/scorecards/`.

## Per-bead Scorecard Entry Fields

Each entry in `agents/scorecards/` records:

| Field | Description |
|---|---|
| `timestamp` | ISO-8601 UTC timestamp |
| `event` | Event type (`bead_completed`, `bead_failed`, `incident`) |
| `bead_id` | BEAD that generated the event |
| `role` | Agent role |
| `mission_id` | Parent mission |
| `validation_passed` | Whether BEAD validation succeeded |
| `budget_used` | Number of tool calls used |
| `incident_count` | Number of incidents during execution |
| `updated_at` | Same as timestamp; identifies when score was mutated |
