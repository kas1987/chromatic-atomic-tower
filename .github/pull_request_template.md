# CAT Pull Request

## Mission

Mission ID: <!-- MP-CAT-[SABC]NNN-[1-4]CNN -->

## BEAD

BEAD ID: <!-- BEAD-CAT-[SABC]NNN-[1-4]CNN-NN -->

Taxonomy source: `gates/CAT_ID_TAXONOMY.yaml`. Historical numeric IDs are
compatibility-only; new work must use the canonical form.

## Summary

<!-- What was done and why -->

## Files changed

<!-- List the key files added or modified -->

## Validation output

```
# paste output of: python scripts/cat_validate.py --all
```

- [ ] `python scripts/cat_check_repo.py`
- [ ] `python scripts/cat_validate.py --all`
- [ ] `python -m pytest -q`
- [ ] Other:

## Evidence

Evidence path: <!-- evidence/reports/xxx.txt -->

## Risk

Risk level: <!-- low / medium / high / critical -->

Priority / P0–P4 display: <!-- stored numeric priority and compatibility display -->
Severity: <!-- critical / high / medium / low -->
Complexity: <!-- M1 / M2 / M3 / M4 -->
Reversibility: <!-- high / medium / low -->
HITL mode: <!-- none / review_required / approval_required / human_only -->

## Checklist

- [ ] Scope respected (only allowed_paths touched)
- [ ] Forbidden paths untouched
- [ ] Evidence artifact written to evidence/reports/
- [ ] Learning log updated if applicable
- [ ] BEAD lifecycle complete (archived)
