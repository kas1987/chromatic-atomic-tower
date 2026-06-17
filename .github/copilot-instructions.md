# Chromatic Atomic Tower — Workspace Agent Instructions

These instructions apply to every agent/chat request in this workspace. They are the
always-on layer of the **Budget Agent Harness**: use expensive models for judgment, local
models for labor, and tools for truth.

## Core behaviour

You operate inside a governed repo harness. Move work forward without damaging the repo,
hiding uncertainty, or claiming unsupported success.

- Inspect current project state before proposing repo edits.
- Prefer small, reviewable patches. Never reformat or rewrite unrelated files.
- Never modify files outside the assigned task/ticket scope unless explicitly justified.
- Never claim tests passed unless test output is present.
- Always list: changed files, commands run, known failures, next action.

## Source of truth

The active control layer lives in `.agent/` and the CAT kernel:

- `.agent/project_state.md` — live project status.
- `.agent/queue.json` — machine-readable ticket queue (each item carries a `bead_id`).
- `.agent/model_routes.yaml` — model routing policy.
- `.agent/governance/` — guardrails, escalation matrix, review gates, risk register.
- `missions/`, `beads/`, `evidence/`, `learnings/` — the CAT mission → BEAD → evidence kernel.

A harness ticket is a *view* of a CAT BEAD. Work is authorised by the BEAD/mission, not by
the model performing it.

## Evidence standard

A completed task must include: ticket/BEAD ID, files changed, diff summary, test commands run,
test results, known failures, next action.

## Stop and escalate to a human / Opus if

- Tests fail after two attempts.
- The task touches auth, secrets, security, deletion, database migration, CI/CD, payment, or
  deploy logic.
- A worker wants to modify more than five files unexpectedly.
- Required files are missing, or the task expands beyond the ticket.

## Hard limits (require explicit human approval)

No merge, push, deploy, publish, delete, migration, credential use, or payment action without
explicit human approval. **No automatic merge to `master`/`main`** — ever. The harness only
moves tickets to `review`/`validating`; humans approve the merge.

## Workflow

```
Architecture (GPT) -> Spec/Ticket (Opus) -> Local worker patch (Kimi/MiniMax)
  -> Local tests/lint (tools) -> Cheap review (MiniMax) -> Review packet
  -> Final review (Opus) -> Human merge decision
```

Use the matching chat mode for each role (see `.github/chatmodes/`). Drive the loop with the
VS Code tasks in `.vscode/tasks.json` (`Harness: Run Ticket`, `CAT: Validate`, etc.).
