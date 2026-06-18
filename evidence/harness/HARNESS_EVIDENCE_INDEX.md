# Harness Evidence Index

**Mission:** MP-CAT-005 — Multi-Model Coding Harness MVP  
**BEAD:** BEAD-CAT-005-005 — Relocate durable harness evidence into evidence plane  
**Generated:** 2026-06-18T00:25:00Z  
**Source:** `.agent/` (originals retained, copies placed here)

---

## Purpose

This directory is a durable, version-controlled snapshot of the harness configuration and governance artifacts from `.agent/`. Source files in `.agent/` remain in place; these copies belong to the evidence plane so they are auditable alongside mission evidence.

---

## Artifact Inventory

### Configuration

| Artifact | Path | Description |
|---|---|---|
| Model routes | `evidence/harness/model_routes.yaml` | Per-role model assignments (Architect, Spec, Worker, Cheap Review, Final Review), fallback chains, rate limits |

### Prompts

| Artifact | Path | Role |
|---|---|---|
| Architect prompt | `evidence/harness/prompts/architect_gpt_prompt.md` | Ticket design (GPT-5.5 / high-reasoning) |
| Spec prompt | `evidence/harness/prompts/spec_opus_prompt.md` | Guardrail and acceptance-criteria generation (Opus) |
| Worker prompt | `evidence/harness/prompts/local_worker_prompt.md` | Implementation (Kimi / MiniMax) |
| Cheap review prompt | `evidence/harness/prompts/cheap_reviewer_prompt.md` | Lint/style review (MiniMax) |
| Final review prompt | `evidence/harness/prompts/final_review_opus_prompt.md` | Approval decision (Opus) |

### Templates

| Artifact | Path | Description |
|---|---|---|
| Review packet | `evidence/harness/templates/review_packet_template.md` | Canonical review packet format |
| Ticket | `evidence/harness/templates/ticket_template.md` | Ticket structure used by Architect |
| Run log | `evidence/harness/templates/run_log_template.md` | Per-run execution log format |

### Governance

| Artifact | Path | Description |
|---|---|---|
| Escalation matrix | `evidence/harness/governance/escalation_matrix.md` | Escalation paths by failure mode |
| Guardrails | `evidence/harness/governance/guardrails.md` | Non-negotiable constraints for all roles |
| Review gates | `evidence/harness/governance/review_gates.md` | Gate criteria for cheap and final review |
| Risk register | `evidence/harness/governance/risk_register.md` | Known risks and mitigations |

---

## Source Location

All artifacts are copied from `.agent/` (originals are intact):

```
.agent/
  model_routes.yaml
  prompts/
  templates/
  governance/
```

**Policy:** `.agent/` is the live configuration. `evidence/harness/` is the auditable snapshot tied to BEAD-CAT-005-005 completion.
