# Worker Output

## Ticket ID

CI-001

## Summary

Updated `.github/workflows/validate-cat.yml` to add pytest to the validate job and correct the push trigger branch from `main` to `master`.

## Files Changed

- `.github/workflows/validate-cat.yml`

## Commands Run

```bash
python -m pytest -q tests/test_ci_workflow.py
```

## Results

All tests in `tests/test_ci_workflow.py` passed.

## Known Risks

- None identified. Change is minimal and directly matches ticket requirements.

## Stop / Escalation Notes

- No escalations required.

---

FILE: .github/workflows/validate-cat.yml
```yaml
name: Validate CAT

on:
  pull_request:
  push:
    branches: [master]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python scripts/cat_check_repo.py
      - run: python scripts/cat_validate.py --all
      - run: python scripts/cat_resolve_go.py
      - run: python -m pytest -q
```