# Sprint 010 Plan — GitHub Bridge + PR Governance

## Sprint Objective

Connect CAT to GitHub workflow governance so every branch, PR, commit, issue intake, and changed-file set can be validated against Mission Packs and BEADs.

## Mission

`MP-CAT-A010-4C01_GITHUB_BRIDGE_PR_GOVERNANCE.yaml`

## Sprint BEADs

| BEAD | Title | Output |
|---|---|---|
| BEAD-CAT-A010-4C01-01 | Define GitHub governance contract | Gate rules, docs, playbook, checklist |
| BEAD-CAT-A010-4C01-02 | Implement PR metadata validator | `cat_git_bridge.py`, `cat_branch_name.py` |
| BEAD-CAT-A010-4C01-03 | Implement changed-file scope guard | `cat_changed_files_guard.py` |
| BEAD-CAT-A010-4C01-04 | Implement issue intake scaffold | `cat_issue_intake.py`, issue template |
| BEAD-CAT-A010-4C01-05 | Wire GitHub Bridge CI and docs | Workflow, operator guide, evidence report |

## Exit Criteria

- All BEADs exist and are valid YAML.
- GitHub Bridge CLI validates happy-path PR metadata for A-tier IDs.
- Changed-file guard rejects files outside BEAD scope.
- Issue intake creates draft Mission Pack candidates.
- GitHub Bridge report writes to `evidence/github/reports`.
- Tests pass.
