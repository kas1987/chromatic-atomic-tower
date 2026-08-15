# Start Here — CAT Official Beads + Wiskers

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
python scripts/cat_align_check.py --strict
bd prime
bd ready --json
python scripts/cat_resolve_go.py --check-schema
pytest -q
```

## 3. GitHub Bridge Quick Check

GitHub work must name the official Bead ID and the generated Wisker packet in
its evidence. Do not pass a legacy YAML path to a bridge command.

## 4. Next mission

The active CAT baseline is idle. To start new work:

1. Create an official Beads issue with `bd create`.
2. Include complete `CAT_WISKER_JSON` metadata in its description.
3. Register/approve the corresponding mission in CAT's canonical mission registry.
4. Run `python scripts/cat_resolve_go.py --check-schema`.

## 5. Reference

- `PDR_CAT_A010_GITHUB_BRIDGE_PR_GOVERNANCE.md` — Sprint 010 design record
- `SPRINT_010_PLAN.md` — completed sprint plan
- `playbooks/GITHUB_BRIDGE_PLAYBOOK.md` — GitHub Bridge procedures
- `docs/operations/SPRINT_010_OPERATOR_GUIDE.md` — operator guide
- `CAT_ROADMAP.md` — full sprint lineage
