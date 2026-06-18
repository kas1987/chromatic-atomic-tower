# Quickstart - Sprint 003

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_ci.py --mode local --write-report
pytest -q
```

## CI Scope Check

```bash
python scripts/cat_pr_check.py --mission MP-CAT-003 --bead BEAD-CAT-003-001 --changed-files tests/fixtures/ci/changed_files_allowed.txt
```

## Self-Heal Dry-Run

```bash
python scripts/cat_self_heal.py --dry-run
```
