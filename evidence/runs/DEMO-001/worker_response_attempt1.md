# Worker Output

## Ticket ID

DEMO-001

## Summary

Created `scripts/harness_demo.py` with the three required utility functions: `add`, `is_even`, and `slugify`. All implementations use only stdlib and satisfy the described behavior. Ran the required pytest command and confirmed all 14 tests pass.

## Files Changed

- `scripts/harness_demo.py` (created)

## Commands Run

```bash
python -m pytest -q tests/test_harness_demo.py
```

## Results

```text
14 passed in 0.03s
```

## Known Risks

- None identified. The implementation is small, uses only stdlib, and all existing tests pass.

## Stop / Escalation Notes

- No escalation required. Task completed within scope on the first attempt.

FILE: scripts/harness_demo.py
```python
import re


def add(a, b):
    """Return the arithmetic sum of a and b."""
    return a + b


def is_even(n):
    """Return True if n is even, False otherwise."""
    return n % 2 == 0


def slugify(s):
    """Lowercase, strip, and collapse internal whitespace runs to a single hyphen."""
    return re.sub(r"\s+", "-", s.strip().lower())
```