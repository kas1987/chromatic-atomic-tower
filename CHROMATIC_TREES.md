# ChromaticTrees

ChromaticTrees is the source of truth for repo tree governance.

CAT uses ChromaticTrees to stop folder drift, duplicate governance, and agent wandering.

## Tree doctrine

1. Every top-level directory must have a defined owner plane.
2. Operational authority lives in YAML/JSON contracts.
3. Human rationale lives in Markdown.
4. Agents defer to `CAT_MANIFEST.md` and `CHROMATIC_TREES.md` before adding files.
5. New folders require a manifest update or mission approval.

## Worktree map

```json
{
  "missions": "Mission Plane",
  "beads": "Execution Plane",
  "agents": "Agent Plane",
  "gates": "Gate Plane",
  "evidence": "Evidence Plane",
  "schemas": "Contract Plane",
  "scripts": "Automation Plane",
  "playbooks": "Governance Plane",
  "docs": "Knowledge Plane",
  "state": "State Plane",
  "learnings": "Learning Plane",
  "prompts": "Prompt Plane",
  "checklists": "Review Plane",
  "reference": "Reference Plane"
}
```

## Add-file rule

Before creating a file, answer:

1. Which plane owns it?
2. Which mission and BEAD authorized it?
3. Is there an existing canonical file that should be updated instead?
4. Is it operational contract, evidence, learning, or documentation?

## Bridge block for agent tools

Agents must not duplicate tree rules in separate local instruction files. They may summarize this file, but the source remains `CHROMATIC_TREES.md`.
