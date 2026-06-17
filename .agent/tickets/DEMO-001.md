# Ticket: DEMO-001 Implement harness_demo.py utility functions

## Priority
p1

## Objective

Create `scripts/harness_demo.py` implementing three utility functions — `add`, `is_even`, and `slugify` — so that all tests in `tests/test_harness_demo.py` pass.

## Context

This is the first live worker ticket for the Budget Agent Harness (MP-CAT-002). The test file already exists at `tests/test_harness_demo.py` and imports from `scripts/harness_demo`. The worker must create `scripts/harness_demo.py` with the correct implementations. No other files should be touched.

The three functions required:

1. `add(a, b)` — return the arithmetic sum `a + b`.
2. `is_even(n)` — return `True` if `n` is even, `False` otherwise. Return type must be `bool`.
3. `slugify(s)` — lowercase the string, strip leading/trailing whitespace, collapse all internal whitespace runs to a single hyphen. Example: `"Hello World"` → `"hello-world"`, `"  A  B  "` → `"a-b"`.

## Allowed Files

- `scripts/harness_demo.py`

## Blocked Actions

- Do not modify files outside allowed list.
- Do not change dependencies or install packages.
- Do not perform destructive actions.
- Do not modify `tests/test_harness_demo.py`.
- Do not import third-party libraries (stdlib only).

## Required Commands

```bash
python -m pytest -q tests/test_harness_demo.py
```

## Output Required

- Complete contents of `scripts/harness_demo.py` as a FILE block
- Worker summary
- Known risks

## Acceptance Criteria

- `add(2, 3) == 5`
- `add(-1, 1) == 0`
- `is_even(4) is True`
- `is_even(7) is False`
- `slugify("Hello World") == "hello-world"`
- `slugify("  A  B  ") == "a-b"`
- All 14 tests in `tests/test_harness_demo.py` pass
- Only `scripts/harness_demo.py` is created or modified

## Stop Conditions

Stop and report if:

- The task requires creating or modifying any file other than `scripts/harness_demo.py`
- The implementation requires a non-stdlib dependency
- The tests cannot be satisfied by the described function signatures
- More than 2 implementation attempts fail
