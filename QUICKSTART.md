# Quickstart

## 1. Unpack

```bash
unzip chromatic_atomic_tower_sprint_000.zip
cd chromatic_atomic_tower_sprint_000
```

## 2. Create local environment

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 3. Check the repo

```bash
python scripts/cat_check_repo.py
```

## 4. Validate CAT contracts

```bash
python scripts/cat_validate.py --all
```

## 5. Resolve GO

```bash
python scripts/cat_resolve_go.py
```

## 6. Start a new mission

```bash
python scripts/cat_new_mission.py --template M2_INTERMEDIATE --id MP-CAT-001 --title "Example Mission"
```

## 7. Start a new BEAD

```bash
python scripts/cat_new_bead.py --id BEAD-CAT-001-001 --mission MP-CAT-001 --title "Example Atomic Task"
```

## 8. Close a BEAD after work

```bash
python scripts/cat_closeout.py --bead BEAD-CAT-000-001 --result passed --summary "Repo foundation validated."
```
