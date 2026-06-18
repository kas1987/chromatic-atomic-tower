# Model Routing Playbook

## Purpose

Route work to the right model or agent style without making model choice the primary system design.

## Routing table

| Task | Preferred role | Model style |
|---|---|---|
| Mission planning | Orchestrator / Architect | high reasoning |
| Repo search | Scout | fast context model |
| Code patch | Builder | coding model |
| Review | Reviewer / Auditor | critical reasoning |
| Security | Security | conservative model |
| Documentation | Scribe | clear writing model |

## Rule

The mission and BEAD define the work. The model only performs the assigned role.

## ID-Informed Routing Hints

ID metadata can guide routing defaults while preserving governance authority.

- Mission priority tier (`S|A|B|C`) and complexity marker (`1C..4C`) can set router profile defaults.
- Mission and BEAD contracts remain the source of authority.
- Model capability must never override mission/BEAD gates.

| ID Signal | Suggested Profile | Worker/Review Bias |
|---|---|---|
| `S` tier or `4C` | high_judgment | strongest reasoning on review and escalations |
| `A/B` with `2C/3C` | balanced | standard coding worker plus critical cheap review |
| `C` with `1C` | fast_path | faster worker path with normal gate checks |
