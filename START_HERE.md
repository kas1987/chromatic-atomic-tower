# Start Here - CAT (Post Sprint 010)

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
pytest -q
```

## 3. GitHub Bridge Quick Check

```bash
python scripts/cat_git_bridge.py validate-pr \
  --title "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --branch feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract \
  --commit-message "[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract" \
  --bead beads/completed/BEAD-CAT-A010-4C01-01.yaml \
  --changed-files tests/fixtures/github/changed_files_allowed.txt \
  --write-report
```

## 4. Next Sprint

Sprint 010 (`MP-CAT-A010-4C01`) is **closed**. To start Sprint 011:

1. Review `missions/backlog/MP-CAT-A011-4C01_AGENT_SCORECARD_AUTOMATION.yaml`
2. Expand mission pack and create BEADs
3. Transition `MP-CAT-A011-4C01` from `draft` → `approved`
4. Run `python scripts/cat_resolve_go.py`

## 5. Reference

- `PDR_CAT_A010_GITHUB_BRIDGE_PR_GOVERNANCE.md` — Sprint 010 design record
- `SPRINT_010_PLAN.md` — completed sprint plan
- `playbooks/GITHUB_BRIDGE_PLAYBOOK.md` — GitHub Bridge procedures
- `docs/operations/SPRINT_010_OPERATOR_GUIDE.md` — operator guide
- `CAT_ROADMAP.md` — full sprint lineage
