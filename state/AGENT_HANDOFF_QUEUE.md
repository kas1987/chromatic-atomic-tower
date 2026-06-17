# Agent Handoff Queue

## Queue policy

Agents must work the first unblocked BEAD unless the Orchestrator selects a different approved BEAD with documented reason.

## Active queue

| Order | BEAD | Mission | Role | Status | Reason |
|---:|---|---|---|---|---|
| 1 | BEAD-CAT-000-001 | MP-CAT-000 | Scribe/Orchestrator | active | Establish baseline repo skeleton |
| 2 | BEAD-CAT-000-002 | MP-CAT-000 | Builder/Reviewer | queued | Validate schemas and examples |
| 3 | BEAD-CAT-000-003 | MP-CAT-000 | Orchestrator/Auditor | queued | Prove GO resolver behavior |
| 4 | BEAD-CAT-000-004 | MP-CAT-000 | Scribe/Auditor | queued | Close sprint with evidence and learning |
