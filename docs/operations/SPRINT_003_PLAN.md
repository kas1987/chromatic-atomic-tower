# Sprint 003 Plan: CI Governance and Self-Healing Validation

## Sprint Goal

Build the first enforceable CI governance spine for CAT so Mission Packs, BEADs, state, evidence, and PR scope are automatically validated.

## Operating Principle

> No CI Pass = No Promotion.

## Sprint Deliverables

1. CI governance rules.
2. CI GitHub Actions workflow.
3. CI local runner script.
4. PR scope validator.
5. Failure classifier.
6. Bounded self-healing validator.
7. CI report and failure schemas.
8. Sprint 003 Mission Pack and BEADs.
9. CI playbook, checklist, and operator guide.
10. Tests and example fixtures.

## BEAD Sequence

| BEAD | Title | Purpose |
|---|---|---|
| BEAD-CAT-003-001 | Define CI governance rules and workflow | Establish the CI contract. |
| BEAD-CAT-003-002 | Implement PR scope and failure classification | Validate changed files and route failures. |
| BEAD-CAT-003-003 | Implement bounded self-healing | Repair only safe structural issues. |
| BEAD-CAT-003-004 | Add reports, tests, docs, and prompt pack | Make Sprint 003 complete and usable. |

## Validation Commands

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_ci.py --mode local --write-report
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_allowed.txt
python scripts/cat_self_heal.py --dry-run
pytest -q
```

## Definition of Done

- [ ] Mission Pack validates.
- [ ] BEADs validate.
- [ ] CI workflow exists.
- [ ] CI local report generation works.
- [ ] PR checker blocks forbidden changes.
- [ ] Failure classifier emits schema-valid JSON.
- [ ] Self-heal dry-run is safe and explanatory.
- [ ] All tests pass.
- [ ] Operator docs and prompt pack are complete.
