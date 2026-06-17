# Sprint 000 Plan: CAT Core Foundation

## Sprint objective

Create a clean repo foundation that can govern mission-based autonomous work from day one.

## Sprint commitment

Sprint 000 is not about implementing product features. It is about creating the control tower that future features must pass through.

## BEAD breakdown

| BEAD | Title | Owner | Status |
|---|---|---|---|
| BEAD-CAT-000-001 | Establish repo skeleton and canonical manifest | Orchestrator/Scribe | active |
| BEAD-CAT-000-002 | Validate mission and BEAD schemas | Builder/Reviewer | queued |
| BEAD-CAT-000-003 | Prove GO resolver returns next action | Orchestrator/Auditor | queued |
| BEAD-CAT-000-004 | Close sprint with evidence and learning log | Scribe/Auditor | queued |

## Sprint acceptance

- Repo check passes.
- Schema validation passes.
- GO resolver selects next BEAD.
- Reference docs and prompts exist.
- Commit is traceable to MP-CAT-000 and BEAD-CAT-000-001.

## Sprint stop conditions

- Missing owner decision.
- Mission or BEAD schema fails and cannot be fixed within scope.
- Agent wants to migrate large chunks from V2 without extraction review.
- A requested change has no active BEAD.
- Any secret, token, private credential, or production resource appears.
