# Files, Resources, Tools, Agents, Skills Map

## Target repo placement

| Concept | Target location | Reason |
|---|---|---|
| Mission packs | `missions/` | Mission Plane |
| BEADs | `beads/` | Execution Plane |
| Agents | `agents/roles/` | Execution Plane |
| Skills | `agents/skills/` | Agent capability registry without adding root dir |
| Model routing | `agents/model_routes.yaml` (`roles` + `complexity_routing`) | Orchestration policy (single source of truth) |
| Tools | `scripts/` and `.github/workflows/` | Executable validation and CI/CD automation |
| Resources | `docs/architecture/`, `docs/operations/`, `playbooks/` | Knowledge and operator guidance |
| Gates | `gates/` | Governance and promotion controls |
| Evidence templates | `evidence/templates/` | Evidence Plane |
| Schemas | `schemas/` | Contract Plane |
| Tests | `tests/` | Substantive validation |
| Learning | `learnings/` | Learning Plane |

## Tool stack

| Tool | Purpose |
|---|---|
| `cat_validate_harness_alignment.py` | Validates mission, BEAD, gates, routing, and docs linkage |
| `cat_validate_mermaid.py` | Checks architecture docs contain valid Mermaid fences |
| `cat_generate_evidence_bundle.py` | Creates evidence bundle skeleton |
| `cat_score_confidence.py` | Calculates confidence decision from gate components |
| `cat-governance-ci.yml` | Runs PR/push validation |
| `cat-cd-promotion.yml` | Scores and gates promotion |

## Agent stack

| Agent | Primary job |
|---|---|
| Orchestrator | Selects BEAD, routes model, dispatches |
| Scout | Gathers context and risks |
| Builder | Executes scoped work |
| Reviewer | Checks correctness and quality |
| Auditor | Checks controls and evidence |
| Security | Stops unsafe paths and actions |
| Scribe | Maintains evidence and learning |
