# CI Governance Playbook

## Purpose

This playbook governs how CAT validates work through CI before promotion, review, or closeout.

## Required Checks

| Check | Command | Required |
|---|---|---:|
| Repo structure | `python scripts/cat_check_repo.py` | Yes |
| Schema validation | `python scripts/cat_validate.py --all` | Yes |
| Tower status | `python scripts/cat_status.py` | Yes |
| Evidence validation | `python scripts/cat_evidence.py validate-all` | Yes when bundles exist |
| PR scope | `python scripts/cat_pr_check.py` | PR only |
| Tests | `pytest -q` | Yes |
| CI report | `python scripts/cat_ci.py --write-report` | Yes |

## Failure Routing

| Failure | Route |
|---|---|
| schema_failure | Builder or Scribe |
| state_failure | Orchestrator |
| evidence_failure | Scribe or Auditor |
| test_failure | Builder |
| security_failure | Security and Human Gate |
| scope_failure | Auditor |
| unknown_failure | Human Gate |

## Hard Stops

Stop immediately if CI detects:

- forbidden path mutation
- secret exposure
- production path modification
- missing Mission ID
- missing BEAD ID
- evidence fabrication pattern
- irreversible state change

## Self-Heal Rule

Self-heal may only perform safe structural repair. It may never alter truth-bearing artifacts.
