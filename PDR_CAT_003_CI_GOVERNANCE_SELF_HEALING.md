# PDR-CAT-003: CI Governance and Self-Healing Validation Engine

## 1. Executive Summary

Sprint 003 turns CAT's rules into enforceable automation. Sprint 000 created the core repo, Sprint 001 created deterministic state transitions, and Sprint 002 created evidence-driven closeout. Sprint 003 adds the CI governance spine that continuously validates Mission Packs, BEADs, state, evidence, PR scope, and safe self-healing behavior.

The core operating rule is:

> No CI Pass = No Promotion.

This sprint does not introduce production deployment. It creates the quality-control runway required before CAT can safely drive autonomous work through GO-mode.

## 2. Problem Statement

CAT now has mission contracts, BEAD contracts, transition rules, and evidence bundles. Without CI enforcement, those rules can still be bypassed by manual error, rushed agent output, stale state, or unsupported closeout claims.

The problem is not simply that tests need to run. The deeper problem is that CAT needs an external governance layer that can say:

- This mission is structurally valid.
- This BEAD is allowed to run.
- This evidence bundle is real enough to consider.
- This state transition is legal.
- This PR did not mutate forbidden paths.
- This failure is safe to self-heal or must be escalated.

## 3. Goals

1. Add a first-class CI governance workflow.
2. Add PR scope validation against active BEAD contracts.
3. Add machine-readable CI rule definitions.
4. Add CI summary and report generation.
5. Add failure classification for routing and learning.
6. Add bounded self-healing for safe structural failures.
7. Add tests and documentation for all new CI behavior.
8. Preserve CAT's core rule: self-healing may repair structure, never truth.

## 4. Non-Goals

- No production CD rollout.
- No secret handling or secret repair.
- No remote GitHub API mutation from scripts.
- No automatic code rewrites for application logic.
- No automatic state transition application from CI.
- No fabricated tests, fabricated evidence, or fabricated closeout artifacts.

## 5. Scope

### In Scope

- `.github/workflows/cat-ci.yml`
- `gates/ci/CI_GOVERNANCE_RULES.yaml`
- `schemas/ci_failure.schema.json`
- `schemas/ci_report.schema.json`
- `scripts/cat_ci.py`
- `scripts/cat_pr_check.py`
- `scripts/cat_self_heal.py`
- `scripts/cat_classify_failure.py`
- CI evidence output folders
- Sprint 003 Mission Pack and BEADs
- CI playbook, checklist, operator guide, and Pro GPT prompt
- Tests for CI governance, PR checking, failure classification, and self-healing

### Out of Scope

- Deployment workflows
- Release automation
- Environment promotion
- Secret retrieval
- External artifact storage
- Cloud runner provisioning
- Multi-repo orchestration

## 6. Architecture

Sprint 003 adds a CI governance layer that sits across all four CAT control planes.

```text
Mission Plane      -> mission schema and registry checks
Execution Plane    -> BEAD scope and PR file checks
Evidence Plane     -> evidence bundle and test report checks
Learning Plane     -> failure classification and self-heal routing
```

### CI Pipeline

```text
checkout
  -> setup python
  -> install dependencies
  -> repo structure check
  -> schema validation
  -> state status check
  -> evidence validation
  -> PR scope check
  -> pytest
  -> CI summary report
  -> artifact upload
```

### Self-Healing Boundary

Allowed self-healing:

- create missing required empty directories
- create missing `.gitkeep` placeholders
- regenerate a local CI summary from existing outputs
- normalize safe generated report directories
- report missing optional placeholders

Forbidden self-healing:

- secrets
- production config
- evidence fabrication
- test result fabrication
- mission scope change
- state transition application
- deployment repair
- architecture repair

## 7. Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| CI before CD | Yes | CAT needs enforcement before deployment. |
| PR scope check | Required | Prevents agents from touching files outside their BEAD authority. |
| Self-heal default | Dry-run | Prevents silent mutation. |
| Failure classifier | JSON output | Enables later routing to Orchestrator, Builder, Scribe, Security, or Human Gate. |
| Evidence capture | Markdown + JSON | Human-readable and machine-readable. |
| Artifact upload | GitHub Actions artifact | Keeps CI reports reviewable. |

## 8. Governance Rules

1. **No CI Pass = No Promotion**
2. **No PR Scope Match = No Merge**
3. **No Evidence Validation = No Closeout**
4. **No Safe Repair Class = No Self-Heal**
5. **No Dry-Run Explanation = No Apply**
6. **No Human Gate Bypass for security, secrets, production, or irreversible actions**

## 9. Acceptance Criteria

- CI workflow exists and runs CAT validation steps.
- CI rules are machine-readable.
- CI report schema validates generated report shape.
- Failure classification emits valid JSON.
- PR checker validates Mission/BEAD IDs and changed-file scope.
- PR checker blocks forbidden paths.
- Self-heal supports dry-run and apply modes.
- Self-heal only performs safe structural repairs.
- Tests cover pass, fail, blocked, and dry-run paths.
- Operator guide explains Sprint 003 usage.

## 10. Validation Plan

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_status.py
python scripts/cat_ci.py --mode local --write-report
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_allowed.txt
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_forbidden.txt
python scripts/cat_classify_failure.py --check schema --message "schema validation failed"
python scripts/cat_self_heal.py --dry-run
pytest -q
```

## 11. Rollback Plan

Revert Sprint 003 files:

- CI workflow
- CI rules
- CI scripts
- CI schemas
- Sprint 003 docs
- Sprint 003 Mission Pack and BEADs
- Sprint 003 tests

Preserve any generated CI evidence if it reflects real validation activity.

## 12. Human Gate

Human approval is required before:

- enabling apply-mode self-healing in protected branches
- adding CD/deployment automation
- allowing CI to mutate repo state
- changing protected path rules
- allowing external secrets or cloud integrations

## 13. Closeout Criteria

Sprint 003 is complete when:

- All included tests pass.
- CAT validation passes.
- CI local runner produces report files.
- PR checker blocks forbidden changes.
- Self-heal dry-run explains safe repairs.
- Documentation and prompts are complete.
