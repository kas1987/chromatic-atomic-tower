# MP-CAT-006 Naming Cutover Handoff

## Scope

This handoff captures only the naming-cutover rollout files.

## Files in scope

- scripts/cat_validate.py
- scripts/cat_new_mission.py
- scripts/cat_new_bead.py
- missions/README.md
- beads/README.md
- playbooks/MODEL_ROUTING_PLAYBOOK.md
- reference/README.md
- reference/ID_CROSSWALK_TEMPLATE.md
- tests/test_id_policy.py
- evidence/reports/mp_cat_006_naming_cutover_validation.md
- learnings/DECISION_LOG.md

## Diff summary

- 8 tracked files changed
- 245 insertions, 8 deletions
- 3 new files added in this scope

## Verification

Commands run:

```bash
python -m pytest -q tests/test_id_policy.py
python scripts/cat_validate.py --all
```

Results:

- `8 passed in 0.11s`
- `CAT validation passed.`

## Commit Message Draft

```text
feat(cat): enforce new-work mission/bead naming cutover with routing alignment

- add naming policy enforcement in scripts/cat_validate.py
  - support new format: MP-CAT-S001-4C01 and mission-stem bead IDs
  - grandfather legacy IDs below MP-CAT-006 cutover
  - enforce mission/bead compatibility for new-format missions
- update creators
  - scripts/cat_new_mission.py defaults to new mission format
  - scripts/cat_new_bead.py adds mission-stem sequence generation and validation
- document policy and router alignment
  - missions/README.md, beads/README.md, playbooks/MODEL_ROUTING_PLAYBOOK.md
  - reference/README.md + new reference/ID_CROSSWALK_TEMPLATE.md
- add targeted tests in tests/test_id_policy.py
- log governance evidence and decision
  - evidence/reports/mp_cat_006_naming_cutover_validation.md
  - learnings/DECISION_LOG.md

Validation:
- python -m pytest -q tests/test_id_policy.py
- python scripts/cat_validate.py --all
```

## Scoped Commit Commands

```bash
git add scripts/cat_validate.py scripts/cat_new_mission.py scripts/cat_new_bead.py missions/README.md beads/README.md playbooks/MODEL_ROUTING_PLAYBOOK.md reference/README.md reference/ID_CROSSWALK_TEMPLATE.md tests/test_id_policy.py evidence/reports/mp_cat_006_naming_cutover_validation.md learnings/DECISION_LOG.md

git commit -m "feat(cat): enforce new-work mission/bead naming cutover with routing alignment"
```

