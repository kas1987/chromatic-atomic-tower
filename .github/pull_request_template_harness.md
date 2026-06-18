# Harness PR Template

## Mission / BEAD

- Mission ID:
- BEAD ID(s):
- Complexity: M1 / M2 / M3 / M4

## Scope

What changed?

## Assertions addressed

- [ ] Completeness
- [ ] Substantive validation
- [ ] Control validation
- [ ] Evidence sufficiency
- [ ] Routing / classification
- [ ] Presentation / disclosure

## Validation

- [ ] `python scripts/cat_check_repo.py`
- [ ] `python scripts/cat_validate.py --all`
- [ ] `python scripts/cat_validate_harness_alignment.py --root .`
- [ ] `python scripts/cat_validate_mermaid.py --root .`
- [ ] `pytest -q`

## Evidence

Attach or link evidence bundle.

## Exceptions

List unresolved risks, limitations, or deviations.

## Approval

- [ ] Reviewer
- [ ] Auditor
- [ ] Human owner for M4
- [ ] Security if applicable
