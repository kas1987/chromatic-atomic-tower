# Start Here - CAT Sprint 003

## 1. Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 2. Validate the Package

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_ci.py --mode local --write-report
pytest -q
```

## 3. Resolve GO

```bash
python scripts/cat_resolve_go.py
```

Expected active work:

```text
Mission: MP-CAT-003
BEAD: BEAD-CAT-003-001
```

## 4. Review Sprint 003

Read:

- `PDR_CAT_003_CI_GOVERNANCE_SELF_HEALING.md`
- `SPRINT_003_PLAN.md`
- `docs/operations/SPRINT_003_OPERATOR_GUIDE.md`
- `playbooks/CI_GOVERNANCE_PLAYBOOK.md`
