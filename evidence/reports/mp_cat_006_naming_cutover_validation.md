# MP-CAT-006 Naming Cutover Validation

- Mission context: MP-CAT-A006-4C01 (naming and router alignment)
- Type: policy_validation
- Validation result: passed
- Created by: GitHub Copilot (GPT-5.3-Codex)
- Created at: 2026-06-17

## Summary

Implemented and validated new-work naming policy enforcement with backward compatibility for existing mission-stem BEAD IDs.

### Scope delivered

- Enforced mission and BEAD naming policy in validator.
- Added creator-script defaults for new mission and BEAD naming styles.
- Documented cutover and routing-alignment policy in governance docs.
- Added reference crosswalk template for legacy-to-new mapping.
- Added targeted tests for ID policy branches.

## Files changed

- scripts/cat_validate.py
- scripts/cat_new_mission.py
- scripts/cat_new_bead.py
- missions/README.md
- beads/README.md
- playbooks/MODEL_ROUTING_PLAYBOOK.md
- reference/README.md
- reference/ID_CROSSWALK_TEMPLATE.md
- tests/test_id_policy.py

## Validation commands

```bash
python -m pytest -q tests/test_id_policy.py
python scripts/cat_validate.py --all
```

## Validation results

```text
8 passed in 0.11s
CAT validation passed.
```

## Notes

- Cutover policy blocks new legacy numeric mission IDs at MP-CAT-006 and above.
- Existing mission-stem BEAD files using BEAD prefix remain valid to avoid forced churn.
- New generated mission-stem BEAD IDs default to BD prefix in generator flow.
