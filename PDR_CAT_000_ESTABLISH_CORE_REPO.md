# PDR-CAT-000: Establish Chromatic Atomic Tower Core Repo

## 0. Record metadata

| Field | Value |
|---|---|
| PDR ID | PDR-CAT-000 |
| Mission | MP-CAT-000 |
| Sprint | Sprint 000 |
| Title | Establish Chromatic Atomic Tower Core Repo |
| Status | Approved Baseline |
| Owner | Human Owner / Harness Engineer |
| Governance Level | High |
| Complexity | M3 Complex |
| Initial Autonomy | L3 scoped patch, L4 orchestrated continuation after validation |
| Created | 2026-06-17 |
| Last Updated | 2026-06-17 |

## 1. Purpose

Chromatic Atomic Tower (CAT) establishes the clean command-and-control kernel for future Harness work.

The purpose of Sprint 000 is to create a fresh repo that is small, strict, machine-readable, and ready for autonomous engineering without inheriting Harness V2 sprawl.

## 2. Problem statement

Harness V2 contains valuable governance ideas, templates, and playbooks, but it has grown as a broad knowledge base. The next system needs to operate as a control tower rather than another documentation pile.

The current risk is that agents can still:

- read too broadly
- mutate without a validated mission contract
- treat prose as operational authority
- skip evidence capture
- close work without validation
- repeat old decisions
- wander under vague `GO` commands

CAT solves that by making work traceable from Mission -> BEAD -> Agent -> Evidence -> Learning.

## 3. Design thesis

CAT should be:

1. **Schema-first**: missions and BEADs validate before execution.
2. **BEAD-first**: agents work on atomic slices, not broad objectives.
3. **Evidence-first**: closeout requires proof.
4. **Gate-first**: confidence, review, human, promotion, and tool-budget gates are explicit.
5. **GO-mode ready**: `GO` resolves to the next approved, unblocked, high-confidence BEAD.
6. **Small by default**: no unnecessary frameworks, no duplicated governance, no vague playbooks.

## 4. Scope

### In scope

- New CAT repo skeleton
- Mission registry
- Mission templates M1-M4
- BEAD template and active BEADs
- Agent roles and scorecards
- Confidence gate
- Review gate
- Human gate
- Tool budget rules
- Promotion/demotion rules
- Evidence folder system
- JSON schemas
- Validation scripts
- GO resolver MVP
- GPT/agent operating prompts
- GitHub workflow and PR/issue templates
- Harness V2 donor extraction plan

### Out of scope for Sprint 000

- Production deployment automation
- Multi-agent swarm execution
- Full GitHub API integration
- Full state mutation engine
- Secret management
- Cloud infrastructure
- UI dashboard
- Database-backed mission store

## 5. Users and actors

| Actor | Need |
|---|---|
| Human Owner | Type `GO` and receive controlled progress |
| Orchestrator | Select next BEAD without wandering |
| Builder | Implement a narrowly scoped task |
| Reviewer | Verify evidence and scope compliance |
| Auditor | Check governance compliance |
| Scribe | Update logs and learning records |
| Security | Halt unsafe work and require human gates |

## 6. System architecture

CAT uses four control planes.

### 6.1 Mission Plane

Owns what work exists.

Files:

- `missions/registry/MISSION_REGISTRY.yaml`
- `missions/active/`
- `missions/templates/`
- `state/TOWER_STATE.yaml`

### 6.2 Execution Plane

Owns what agents may do.

Files:

- `beads/active/`
- `beads/templates/`
- `agents/`
- `gates/`
- `scripts/cat_resolve_go.py`

### 6.3 Evidence Plane

Owns proof.

Files:

- `evidence/`
- `schemas/evidence.schema.json`
- `playbooks/VALIDATION_PLAYBOOK.md`
- `checklists/CLOSEOUT_CHECKLIST.md`

### 6.4 Learning Plane

Owns improvement.

Files:

- `learnings/DECISION_LOG.md`
- `learnings/INCIDENT_LOG.md`
- `learnings/ECHO_LOG.md`
- `learnings/PATTERN_LIBRARY.md`
- `agents/registry/AGENT_SCORECARD.yaml`

## 7. Mission state model

```text
DRAFT -> TRIAGED -> APPROVED -> DISPATCHED -> IN_PROGRESS -> VALIDATING -> REVIEWED -> CLOSED -> LEARNED
```

Exception states:

```text
BLOCKED
ESCALATED
ROLLED_BACK
ABANDONED
INCIDENT
```

Each state transition requires evidence. No mission moves because an agent says it moved.

## 8. Complexity model

CAT keeps the M1-M4 mission model:

| Level | Meaning | Default governance |
|---|---|---|
| M1 Basic | Small, low-risk, simple task | Standard |
| M2 Intermediate | Multiple steps, modest risk | Elevated |
| M3 Complex | Multiple systems or broad impact | High |
| M4 Atomic | Critical, irreversible, high-risk | Maximum |

Complexity does not alone determine autonomy. CAT also scores risk and reversibility.

## 9. Autonomy model

| Level | Name | Allowed behavior |
|---|---|---|
| L0 | Read Only | Inspect and report |
| L1 | Plan | Propose actions only |
| L2 | Draft | Create proposed changes |
| L3 | Patch | Apply scoped changes and validate |
| L4 | Continue | Select next approved BEAD |
| L5 | Tower | Multi-agent coordination with gates |

Sprint 000 starts at L3 for implementation and L4 for deterministic GO-mode resolution.

## 10. Confidence gate

CAT uses a weighted score:

```text
Confidence = objective clarity 20% + scope clarity 20% + evidence quality 20% + reversibility 10% + tool fit 10% + risk awareness 10% + testability 10%
```

Action bands:

| Score | Band | Behavior |
|---:|---|---|
| 90-100 | Very High | Execute scoped work |
| 75-89 | High | Execute with normal logging |
| 60-74 | Medium | Reversible low-risk work only |
| 40-59 | Low | Plan only |
| 0-39 | Blocked | Halt and escalate |

Human gates override confidence.

## 11. Functional requirements

| ID | Requirement | Acceptance |
|---|---|---|
| FR-001 | Repo has canonical tree | `cat_check_repo.py` passes |
| FR-002 | Mission contracts validate | `cat_validate.py --all` passes |
| FR-003 | BEAD contracts validate | `cat_validate.py --all` passes |
| FR-004 | GO resolver selects next BEAD | `cat_resolve_go.py` prints dispatch packet |
| FR-005 | Agents have role boundaries | `agents/roles/*.md` exists |
| FR-006 | Gates are documented | `gates/**/*.md` exists |
| FR-007 | Evidence folders exist | `evidence/*/.gitkeep` exists |
| FR-008 | V2 migration path exists | `docs/migration/HARNESS_V2_EXTRACTION_PLAN.md` exists |

## 12. Non-functional requirements

| Area | Requirement |
|---|---|
| Simplicity | Scripts must run locally with Python 3.11+ |
| Portability | Repo must work without external services |
| Traceability | Every active BEAD maps to a mission |
| Safety | Forbidden paths must be explicit |
| Auditability | Work must produce evidence before closeout |
| Agent usability | Prompts and read order must be explicit |

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Overbuilding CAT | Slow adoption | Sprint 000 is skeleton and contracts only |
| Legacy sprawl migrates in | Confusing repo | V2 is donor, not foundation |
| Agents use docs as permission | Scope creep | Execution contracts define authority |
| GO-mode wanders | Unsafe work | GO resolver reads registry and active BEADs only |
| Evidence becomes optional | Weak governance | Closeout checklist requires evidence |

## 14. Acceptance criteria

Sprint 000 is accepted when:

- `python scripts/cat_check_repo.py` passes.
- `python scripts/cat_validate.py --all` passes.
- `python scripts/cat_resolve_go.py` returns `BEAD-CAT-000-001` as the next dispatchable item.
- Active mission and BEAD files exist.
- Agent role files exist.
- Gate files exist.
- PDR, README, quickstart, prompts, and checklists are complete.

## 15. Rollout plan

1. Create new GitHub repo `chromatic-atomic-tower`.
2. Unzip Sprint 000 package into repo root.
3. Run repo check and validation.
4. Commit baseline.
5. Use `GO` resolver to start BEAD-CAT-000-001.
6. Close BEAD with evidence.
7. Continue BEAD-CAT-000-002.
8. Promote Sprint 001 only after Sprint 000 is validated.

## 16. Decision record

| Decision | Outcome |
|---|---|
| Use new repo | Approved |
| Use Harness V2 as donor only | Approved |
| Use YAML for operational contracts | Approved |
| Use Markdown for rationale and playbooks | Approved |
| Keep Python scripts dependency-light | Approved |
| Make GO deterministic | Approved |

## 17. Next PDR

PDR-CAT-001 should cover the state-transition engine, automated closeout mutation, and GitHub issue/PR integration.
