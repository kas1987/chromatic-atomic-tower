# Evidence Report — BEAD-CAT-005-002

**BEAD:** BEAD-CAT-005-002  
**Mission:** MP-CAT-005 — Multi-Model Coding Harness MVP  
**Title:** Verify and commit worker prompt template  
**Auditor:** Claude Code (Sonnet 4.6)  
**Timestamp:** 2026-06-18T00:30:00Z  
**Autonomy:** L3 · Risk: low · Reversibility: high  

---

## Verification Result: PASS

### Definition of Done — Checklist

| Criterion | Status | Evidence |
|---|---|---|
| `prompts/WORKER_PROMPT_TEMPLATE.md` has OBJECTIVE section | ✅ PASS | Line 9: `## OBJECTIVE` — contains ticket details, scope, and success criteria |
| `prompts/WORKER_PROMPT_TEMPLATE.md` has CONSTRAINTS section | ✅ PASS | Line 37: `## CONSTRAINTS` — scope discipline, quality/safety, iteration/retry, output format |
| `prompts/WORKER_PROMPT_TEMPLATE.md` has OUTPUT SCHEMA section | ✅ PASS | Line 69: `## OUTPUT SCHEMA` — JSON metadata block + unified diff format |
| Evidence report written | ✅ PASS | This file |

### Section Contents Summary

**OBJECTIVE (lines 9–34)**
- Ticket fields: `${TICKET_ID}`, `${TICKET_OBJECTIVE}`, `${ALLOWED_PATHS}`
- 5 success criteria: addresses objective, touches only allowed paths, no breaking API changes, tests pass, follows conventions

**CONSTRAINTS (lines 37–66)**
- Scope Discipline: forbidden paths flagged as stop condition
- Quality & Safety: no destructive commands, no secrets, no hardcoded paths, no breaking migrations
- Iteration & Retry: max 2 attempts, escalate on second failure
- Output Format: required sections REASONING → IMPLEMENTATION → VALIDATION → RISKS → READY FOR REVIEW

**OUTPUT SCHEMA (lines 69–122)**
- JSON metadata block with: `ticket_id`, `worker_model`, `implementation_status`, `files_changed[]`, `tests_run[]`, `approval_required`, `stop_condition_hit`, `next_step`, `evidence_log`
- Diff format: unified diff with 3-line context
- Enum values documented: `complete|incomplete|failed`, `ready_for_cheap_review|escalate_to_review|retry_implementation`

### Additional Content (not required but present)

- `## DECISION TREE` — pre-implementation checklist (context, paths, attempt count, test result)
- `## ROLE IN THE HARNESS` — pipeline position: Architect → Specs → Worker → Cheap Review → Final Review → Human
- `## GLOSSARY` — allowed_paths, forbidden_paths, stop_condition, escalate, implementation_status
- `## EXAMPLE USAGE` — worked example ticket T-2026-001 with expected response structure
- `## REFERENCES` — model_routes.yaml, STATE_MACHINE.md, harness_settings.yaml, ORCHESTRATOR_PROMPT.md

### Validation Command

```
manual — read review of prompts/WORKER_PROMPT_TEMPLATE.md
```

No automated test was required per BEAD definition. The template is a static artifact, not executable code.

---

## Files Inspected

- `prompts/WORKER_PROMPT_TEMPLATE.md` — 233 lines, v0.1.0, dated 2026-06-17 (BEAD-CAT-002-002)

## Files Modified

- `evidence/reports/bead_cat_005_002_worker_prompt.md` (this file, created)

---

## Next Recommended BEAD

**BEAD-CAT-005-003** — next in MP-CAT-005 sequence (implement or verify the next harness component).

---

## Stop Conditions Hit

None. All required sections present. Scope was not expanded.
