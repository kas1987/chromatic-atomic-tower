# CAT Manifest

`CAT_MANIFEST.md` is the canonical repo rulebook for Chromatic Atomic Tower.

If another file conflicts with this manifest, this manifest wins unless a human owner updates the manifest.

## 1. Repository purpose

CAT exists to control mission-based autonomous engineering.

It does not exist to store random notes, broad experiments, or ungoverned prompts.

## 2. Canonical hierarchy

```text
Human Goal
  -> Mission Pack
    -> BEAD
      -> Agent Dispatch
        -> Evidence
          -> Learning
            -> Next BEAD
```

## 3. Required root files

| File | Purpose |
|---|---|
| `README.md` | Human entrypoint |
| `START_HERE.md` | First-run instructions |
| `PDR_CAT_000_ESTABLISH_CORE_REPO.md` | Design record |
| `CAT_MANIFEST.md` | Canonical repo rules |
| `CAT_PRINCIPLES.md` | System principles |
| `CHROMATIC_TREES.md` | Tree governance and worktree map |
| `AGENTS.md` | Agent operating instructions |
| `requirements.txt` | Python script dependencies |
| `Makefile` | Common local commands |

## 4. Canonical directories

| Directory | Owner | Allowed content |
|---|---|---|
| `missions/` | Mission Plane | Mission contracts, templates, registry |
| `beads/` | Execution Plane | Atomic work units |
| `agents/` | Execution Plane | Agent roles and scoring |
| `gates/` | Execution Plane | Confidence, review, human, promotion, tool budget |
| `evidence/` | Evidence Plane | Logs, diffs, reports, screenshots, test results |
| `schemas/` | Contract Plane | JSON schemas |
| `scripts/` | Automation Plane | Validators, resolvers, generators |
| `playbooks/` | Governance Plane | Operating procedures |
| `docs/` | Knowledge Plane | Architecture, operations, migration, reference |
| `state/` | State Plane | Sprint state, tower state, handoff queue, risks |
| `learnings/` | Learning Plane | Decisions, incidents, patterns, echo logs |
| `prompts/` | Agent Plane | Reusable GPT/agent prompts |
| `checklists/` | Review Plane | Human and agent checklists |
| `reference/` | Reference Plane | Source images and supporting artifacts |

## 5. No orphan work rule

No change may be made unless it can identify:

- Mission ID
- BEAD ID
- Agent or human owner
- Allowed path
- Validation method
- Evidence destination

## 6. Mutation rule

Agents may only write files listed in the active BEAD `allowed_paths` field.

Agents must halt if they need to touch a forbidden path or a path not explicitly allowed.

## 7. Documentation rule

Markdown explains why and how.

YAML/JSON defines what is allowed.

If prose conflicts with YAML/JSON execution contract, the execution contract wins for agent action.

## 8. Validation rule

Before closeout, run:

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

## 9. GO-mode rule

`GO` means:

```text
Resolve the highest-priority approved unblocked BEAD and dispatch only that BEAD.
```

`GO` does not mean:

```text
Search broadly, invent work, change architecture, or continue without evidence.
```

## 10. Change rule

Changes to CAT governance require one of:

- a PDR update
- a mission contract
- a decision log entry
- a human owner approval
