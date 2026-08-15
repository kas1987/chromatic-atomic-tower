# CAT Pull Request

## Mission

Mission ID: <!-- MP-CAT-XXXX-XCXX -->

## Official Bead + Wisker

Official Bead ID: <!-- cat-... -->

Wisker packet: <!-- wiskers/packets/WISKER-....yaml -->

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

## Checklist

- [ ] Scope respected (only allowed_paths touched)
- [ ] Forbidden paths untouched
- [ ] Evidence artifact written to evidence/reports/
- [ ] Learning log updated if applicable
- [ ] Evidence validated before official `bd close`
