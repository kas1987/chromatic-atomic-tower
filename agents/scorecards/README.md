# Agent Scorecards

Per-BEAD scorecard increment files are written here by `scripts/cat_agent_scorecard.py`.

Each file records a single scoring event (completed BEAD, failed BEAD, incident).
The canonical trust state is maintained in `agents/registry/AGENT_SCORECARD.yaml`.

## Format

Files are named `{BEAD_ID}_{role}_{event}.yaml` and contain a single history entry:

```yaml
bead_id: BEAD-CAT-A011-4C01-01
role: Builder
event: bead_completed
delta: 5
timestamp: '2026-06-18T06:00:00+00:00'
```

These files are produced by `cat_agent_scorecard.py score-bead --execute` during
BEAD closeout and are archived alongside BEAD evidence.
