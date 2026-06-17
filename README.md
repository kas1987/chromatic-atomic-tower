# Chromatic Atomic Tower - Sprint 000 Core Foundation

Chromatic Atomic Tower (CAT) is the clean repo foundation for mission-first, BEAD-first, evidence-first autonomous engineering.

This package is the first critical sprint: establish the repo kernel, mission registry, BEAD contract, governance gates, validation scripts, and GO-mode resolver.

CAT is designed to pull the strongest ideas from Harness V2 without bringing over legacy sprawl. Harness V2 remains the donor system. CAT becomes the strict control tower.

## What this sprint gives you

- New repo skeleton for `chromatic-atomic-tower`
- PDR for CAT Sprint 000
- Mission registry and active mission
- M1-M4 mission templates
- BEAD templates and active BEADs
- Agent roles, scorecards, and dispatch rules
- Confidence, review, human, promotion, and tool-budget gates
- JSON schemas for missions, BEADs, evidence, logs, agents, registry, and tower state
- Python validators and repo health checks
- Deterministic `GO` resolver MVP
- Pro GPT starter prompts and agent instructions
- GitHub workflow, PR template, issue template, checklists, and migration docs
- Reference image from the Harness V2 Mission Packet M1-M4 framework

## The operating rule

```text
No Mission = No Work
No BEAD = No Dispatch
No Evidence = No Closeout
No Gate = No Promotion
No Registry Entry = No Commit
```

## Quick start

```bash
unzip chromatic_atomic_tower_sprint_000.zip
cd chromatic_atomic_tower_sprint_000
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_resolve_go.py
```

Expected result: the repo health check passes, schemas validate, and the GO resolver prints the next approved BEAD dispatch packet.

## First commit recommendation

```bash
git init
git add .
git commit -m "[MP-CAT-000][BEAD-CAT-000-001] Establish CAT Sprint 000 core foundation"
```

## Repo map

```text
missions/       Mission contracts, templates, registry, active and archived work
beads/          Atomic execution units that agents can safely run
agents/         Agent roles, registry, and scorecards
gates/          Confidence, review, human, promotion, and tool-budget gates
evidence/       Test output, diffs, reports, logs, screenshots, and proof artifacts
schemas/        Machine-readable contracts for CAT objects
scripts/        Validators, GO resolver, generators, and closeout helpers
playbooks/      Human and agent operating procedures
docs/           Architecture, operations, migration, and reference material
state/          Tower state, sprint state, handoff queue, risk register
learnings/      Decision log, incident log, echo log, and reusable patterns
prompts/        Pro GPT, orchestrator, builder, reviewer, and auditor prompts
checklists/     Repo birth, review, implementation, and closeout checklists
reference/      Source reference images and supporting artifacts
.github/        CI workflow, issue template, and PR template
```

## The core loop

```text
Observe -> Classify -> Score -> Decide -> Dispatch -> Execute -> Validate -> Record -> Learn -> Queue Next
```

## First sprint definition of done

Sprint 000 is done when:

- The repo skeleton exists.
- `CAT_MANIFEST.md` is the canonical tree rule source.
- Mission and BEAD schemas validate.
- Active mission `MP-CAT-000` exists.
- Active BEAD queue exists.
- GO resolver returns the next actionable BEAD.
- Evidence folders exist.
- Agents have role boundaries.
- Checklists and playbooks are in place.
- V2 donor extraction plan exists.

## What to build next

After this foundation, Sprint 001 should implement stronger automation:

1. mission state transitions with enforcement
2. BEAD closeout mutation against registry
3. GitHub issue/PR integration
4. evidence artifact indexing
5. agent score updates from closeout results
6. richer GO-mode priority scoring
