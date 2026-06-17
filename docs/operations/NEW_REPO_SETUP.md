# New Repo Setup

## Recommended repo name

```text
chromatic-atomic-tower
```

## Setup steps

```bash
mkdir chromatic-atomic-tower
cd chromatic-atomic-tower
unzip ../chromatic_atomic_tower_sprint_000.zip
git init
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
git add .
git commit -m "[MP-CAT-000][BEAD-CAT-000-001] Establish CAT Sprint 000 core foundation"
```

## Branching recommendation

- `main`: stable validated CAT baseline
- `mission/MP-CAT-000`: mission branch
- `bead/BEAD-CAT-000-001`: atomic work branch if using fine-grained branching
