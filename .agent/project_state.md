> Governed as CAT mission MP-CAT-002. Harness home is .agent/.

# Project State: Budget Agent Harness

## Mission
Run a budget-aware multi-model coding harness using GPT for architecture, Opus for specs/review, and Kimi/MiniMax via Ollama for implementation.

> Governed in CAT as **MP-CAT-002** (Multi-Model Coding Harness MVP). Tickets below map to BEAD-CAT-002-001..004. This file is the human-facing intent; the CAT mission/BEAD contracts are the operational authority.

## Current Objective
Build the first working task loop: ticket → local worker patch → tests → cheap review → Opus final review.

## Constraints
- Minimize Opus calls.
- No direct merge without human approval.
- Local workers may only modify files listed in the ticket unless they explain why.
- Failed tasks stop after 2 retries.
- Destructive actions require explicit approval.

## Active Queue
| ID | BEAD | Status | Priority | Task | Owner | Done When |
|---|---|---|---|---|---|---|
| T001 | BEAD-CAT-002-001 | pending | p1 | Create model route config | GPT/Opus | `agents/model_routes.yaml` exists |
| T002 | BEAD-CAT-002-002 | pending | p1 | Create worker prompt template | Opus | Prompt has objective, constraints, output schema |
| T003 | BEAD-CAT-002-003 | pending | p1 | Run first local worker patch | Kimi/MiniMax | Patch generated and tests run |
| T004 | BEAD-CAT-002-004 | pending | p1 | Create final review packet format | Opus | Review packet template exists |

## Model Routing (verified Ollama Cloud tags)
- architecture → GPT (external Pro GPT, human-mediated) / `gpt-oss:120b-cloud` fallback
- specs, final review → Opus (`claude-opus-4-8`)
- cheap_review → `minimax-m3:cloud`
- implementation (workers) → `kimi-k2.7-code:cloud`, `minimax-m3:cloud`

## Status
MP-CAT-002 mission + 4 BEAD contracts authored and registered (status: draft). Awaiting Human Owner approval (human_gate) to promote and dispatch BEAD-CAT-002-001.
