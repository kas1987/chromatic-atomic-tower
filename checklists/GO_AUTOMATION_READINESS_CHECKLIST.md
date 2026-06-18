# GO Automation Readiness Checklist

Use this checklist before declaring MP-CAT-GO-AUTO-001 complete.

## Minimum Safety
- [ ] `cat_check_repo.py` passes.
- [ ] `cat_validate.py --all` passes.
- [ ] Pytest passes.
- [ ] No scheduled workflows unless budget-approved (CAT_BUDGET_APPROVED annotation).
- [ ] No Windows/macOS runners unless exception-approved (CAT_RUNNER_EXCEPTION annotation).
- [ ] validate-cat.yml has concurrency cancellation.
- [ ] validate-cat.yml has explicit permissions block.
- [ ] validate-cat.yml has timeout-minutes.

## Mission/BEAD Control
- [ ] Active mission exists in registry with `status: approved`.
- [ ] Active BEAD exists in `beads/active/`.
- [ ] BEAD has allowed_paths.
- [ ] BEAD has forbidden_paths.
- [ ] BEAD has validation list.
- [ ] BEAD has definition_of_done.

## Closeout Control
- [ ] Evidence files exist for each BEAD.
- [ ] evidence/manifest.yaml is populated with artifact hashes.
- [ ] Closeout report generated for each BEAD.
- [ ] Registry mutation performed by cat_transition.py, not manual edits.
- [ ] Closed state is terminal (no re-open without incident mission).

## Agent Control
- [ ] Agent ID recorded in scorecard.
- [ ] Tool budget recorded.
- [ ] Scope violations recorded.
- [ ] Validation failures recorded.
- [ ] cat_score_agent.py --dry-run --sample passes.

## GO Resolver
- [ ] cat_resolve_go.py --format json --check-schema passes.
- [ ] Dispatch packet validates against go_dispatch_packet.schema.json.
- [ ] Low-confidence BEADs are blocked (confidence < minimum).
- [ ] JSON and markdown output modes work.
