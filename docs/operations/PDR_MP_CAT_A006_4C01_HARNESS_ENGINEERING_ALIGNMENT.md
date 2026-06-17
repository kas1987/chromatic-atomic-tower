# PDR — MP-CAT-A006-4C01 Harness Engineering Audit Alignment

## Problem

CAT has a strong mission→BEAD→evidence kernel but the audit methodology (assertions,
completeness, control vs substantive validation, evidence hierarchy, complexity-aware model
routing, CI/CD promotion gates) was implicit. Without it, gates are subjective and promotion can
happen without evidence.

## Decision

Add an explicit, machine-readable Harness Engineering audit layer on top of the existing kernel,
adopted as mission **MP-CAT-A006-4C01** (M4, tier A, first mission under the
Type-Repo-Priority-Complexity ID convention). Overlapping concerns EXTEND the kernel rather than
duplicate it (complexity routing folds into `agents/model_routes.yaml`; role audit duties fold
into `agents/roles/*.md`; flat gate contracts sit beside the existing per-stage gate dirs).

## Scope

8 BEADs: assertion gates, completeness model, evidence fabric, skills+routing, governance
playbooks, CI validation, CD promotion, Mermaid docs + learning.

## Validation

`cat_check_repo.py`, `cat_validate.py --all`, `cat_validate_harness_alignment.py`,
`cat_validate_mermaid.py`, `pytest -q`, plus `cat_generate_evidence_bundle.py` and
`cat_score_confidence.py` for promotion.

## Risks & controls

- Governance files added but not enforced → governance CI workflow runs the validators.
- Concurrent-agent corruption (realized 2026-06-17 Codex/VS Code incident) → single-writer +
  git worktrees + PR integration (see CAT_MULTI_AGENT_CONCURRENCY_AND_HAZARD_PROTOCOL.md).
- M4 change merged without human approval → human gate + promotion gate.

## Status

draft (awaiting M4 human approval). Confidence dry-run 90.0 / auto_proceed; all validators pass.
