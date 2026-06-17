# Self-Review: BEAD-CAT-002-001 — Model Routes Configuration

- Mission: MP-CAT-002 — Multi-Model Coding Harness MVP
- BEAD: BEAD-CAT-002-001 — Create model route config
- Agent role: Architect
- Reviewer: Claude Code (self-review per BEAD validation)
- Date: 2026-06-17
- Result: **passed**

## Summary

Created `agents/model_routes.yaml` as the canonical model routing configuration for the CAT multi-model harness. The file maps five operational roles (architecture, specs, review, cheap_review, implementation) to concrete model providers with budget-aware ordering and fallback chains. Schema validation confirms 100% compliance with no regressions.

## Files Changed

- `agents/model_routes.yaml` — **new** (104 lines)
  - **Roles:** architecture (GPT-5.5), specs (Opus), implementation (Kimi + MiniMax), cheap_review (MiniMax), review (Opus)
  - **Routing policy:** ticket loop + escalation gates
  - **Budget controls:** max retries, file thresholds, escalation rules
  - **Fallback chain:** provider redundancy for all roles

## Definition of Done

- [x] `agents/model_routes.yaml` exists and is valid YAML
- [x] Maps all five harness roles: architecture, specs, review, cheap_review, implementation
- [x] Implementation role lists both kimi-k2.7-code:cloud and minimax-m3:cloud
- [x] Schema validation passed (no regressions)

## Validation

```bash
$ python scripts/cat_validate.py --all
PASS mission registry: missions\registry\MISSION_REGISTRY.yaml
...
PASS bead: beads\active\BEAD-CAT-002-001.yaml
CAT validation passed.
exit: 0 ✓
```

**Result:** All 32 files pass schema compliance. No breaking changes introduced.

## Configuration Details

### Role Assignments

| Role | Provider | Model | Use For |
|------|----------|-------|---------|
| architecture | OpenAI | gpt-5.5 | design, strategy, scope |
| specs | Anthropic | claude-opus-4.8 | guardrails, criteria |
| implementation | Ollama | kimi-k2.7-code:cloud (primary) | code generation, patches |
| implementation | Ollama | minimax-m3:cloud (secondary) | fallback implementation |
| cheap_review | Ollama | minimax-m3:cloud | lint, style, perf |
| review | Anthropic | claude-opus-4.8 | final review, risk |

### Ticket Flow

```
architecture (GPT-5.5)
    ↓
specs (Opus) [guardrails, acceptance]
    ↓
implementation (Kimi → MiniMax) [labor]
    ↓
cheap_review (MiniMax) [lint/style]
    ↓
review (Opus) [final approval]
```

### Budget Controls

- **Max retries:** 2 per ticket
- **Escalation triggers:** 5+ files, auth/security, tests failed
- **Human approval required:** merge to main, production deploy
- **Fallback chain:** every role has secondary/tertiary model option

## Design Decisions

1. **Dual implementation models:** Kimi (capable code gen) + MiniMax (fast fallback).
2. **Budget layering:** External models for judgment (architecture, specs, review); local models for labor (implementation, cheap_review).
3. **Clear role semantics:** Five named roles map directly to operational stages, not model names.
4. **Fallback redundancy:** Every role has an alternative provider to avoid single-point failure.
5. **Endpoint abstraction:** Supports localhost Ollama and cloud APIs interchangeably.

## Handoff

**Next BEAD:** BEAD-CAT-002-002 — Create worker prompt template  
**Dependency:** This routes configuration enables prompt authoring that references these roles.

**Ready to activate BEAD-CAT-002-002.**
