# Agent Handoff Queue — Sprint 001

## Active

### BEAD-CAT-001-001 — Define lifecycle transition matrix

- Suggested Agent: Builder
- Reviewer: Auditor
- Mission: MP-CAT-001
- Objective: Finalize state rules for mission and BEAD lifecycle movement.
- Allowed Files: `gates/state/**`, `docs/architecture/STATE_MACHINE.md`, `tests/**`
- Definition of Done: transition rules are machine-readable and tests cover allowed/denied paths.

## Next

### BEAD-CAT-001-002 — Implement transition CLI

- Suggested Agent: Builder
- Objective: Add `scripts/cat_transition.py` with dry-run, apply, audit, registry, and tower-state updates.

### BEAD-CAT-001-003 — Add transition tests and schema checks

- Suggested Agent: Reviewer / QA
- Objective: Validate transition behavior and schema compliance.

### BEAD-CAT-001-004 — Document operator workflow and closeout evidence

- Suggested Agent: Scribe
- Objective: Write operator guide, playbook, evidence report, and closeout checklist.
