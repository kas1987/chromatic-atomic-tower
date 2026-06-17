# Self-Review: BEAD-CAT-002-002 — Worker Prompt Template

- Mission: MP-CAT-002 — Multi-Model Coding Harness MVP
- BEAD: BEAD-CAT-002-002 — Create worker prompt template
- Agent role: Scribe
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Created `prompts/WORKER_PROMPT_TEMPLATE.md` as the canonical instruction set for worker models (Kimi, MiniMax) implementing tickets in the CAT harness. The template provides clear objective/constraints/output sections, references the model routes defined in BEAD-CAT-002-001, and includes a JSON schema for machine-readable handoff to the cheap review stage.

## Files Changed

- `prompts/WORKER_PROMPT_TEMPLATE.md` — **new** (318 lines)
  - **Sections:** Objective, Constraints, Output Schema, Decision Tree, Role Description
  - **Guardrails:** file scope, no secrets, max 2 retries, escalation logic
  - **Output format:** JSON metadata block + unified diffs
  - **Integration:** References model routes, transition engine, harness settings

## Definition of Done

- [x] `prompts/WORKER_PROMPT_TEMPLATE.md` exists
- [x] Contains objective section (ticket context, success criteria)
- [x] Contains constraints section (scope, quality, iteration limits)
- [x] Contains machine-readable output schema (JSON metadata + diffs)
- [x] References model routing from BEAD-CAT-002-001

## Validation

Prompt template structure verified:

1. **Objective Section:** ✓
   - Ticket details placeholder
   - Success criteria (5 items)
   - Scope discipline requirements

2. **Constraints Section:** ✓
   - File scope enforcement
   - Quality & safety guardrails
   - Iteration & retry logic (max 2 attempts)

3. **Output Schema:** ✓
   - JSON metadata block (ticket_id, implementation_status, files_changed, tests_run, etc.)
   - Unified diff format with 3-line context
   - Decision tree for control flow

4. **Integration:** ✓
   - References `agents/model_routes.yaml` (model endpoints, fallback chains)
   - References `docs/architecture/STATE_MACHINE.md` (harness lifecycle)
   - References `.agent/harness_settings.yaml` (budget controls)
   - Integrates with cheap review stage

## Design Decisions

1. **Placeholder variables:** `${TICKET_ID}`, `${ALLOWED_PATHS}`, `${WORKER_MODEL}` allow dynamic injection during ticket loop execution.
2. **Structured output:** JSON metadata enables machine parsing for automated validation and routing decisions.
3. **Escalation semantics:** `implementation_status: incomplete` triggers review escalation; allows worker to signal confidence level.
4. **Retry logic:** Max 2 attempts enforced in template; worker cannot exceed without human intervention.
5. **Examples included:** Full example at end shows usage in context (OAuth2 refactor).
6. **Decision tree:** Helps workers systematically evaluate preconditions before implementation.

## Handoff

**Next BEAD:** BEAD-CAT-002-003 — Run first local worker patch  
**Dependency:** This template enables worker invocation in BEAD-002-003; worker will fill placeholders and execute.

**Template Completeness:**
- ✅ Objective & constraints defined
- ✅ Output schema machine-readable
- ✅ Integration with model routes documented
- ✅ Escalation paths clear
- ✅ Ready for first harness run (BEAD-002-003)

**Ready to activate BEAD-CAT-002-003.**
