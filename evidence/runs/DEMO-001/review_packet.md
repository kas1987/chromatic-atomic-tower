# Review Packet

## Ticket

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


## Files Changed

```text
scripts/harness_demo.py

```

## Diff Summary

```text
 scripts/harness_demo.py | 16 ++++++++++++++++
 1 file changed, 16 insertions(+)

```

## Patch / Targeted Diff

```diff
diff --git a/scripts/harness_demo.py b/scripts/harness_demo.py
new file mode 100644
index 0000000..65c0d04
--- /dev/null
+++ b/scripts/harness_demo.py
@@ -0,0 +1,16 @@
+import re
+
+
+def add(a, b):
+    """Return the arithmetic sum of a and b."""
+    return a + b
+
+
+def is_even(n):
+    """Return True if n is even, False otherwise."""
+    return n % 2 == 0
+
+
+def slugify(s):
+    """Lowercase, strip, and collapse internal whitespace runs to a single hyphen."""
+    return re.sub(r"\s+", "-", s.strip().lower())

```

## Test Commands Run

```text
python -m pytest -q tests/test_harness_demo.py
```

## Test Results

```text
..............                                                           [100%]
14 passed in 0.03s

```

## Worker Self-Assessment

Worker model: kimi-k2.7-code:cloud
Attempts used: 1 / 2
Files written: ['scripts/harness_demo.py']
Guardrail violations: []
Escalation notes: []

## Cheap Reviewer Notes

# Cheap Review

## Decision
APPROVE

## Findings
- `scripts/harness_demo.py`: Clean, correct implementation. All three functions match the ticket spec.
  - `add`: trivial `a + b` — correct.
  - `is_even`: `n % 2 == 0` returns native `bool` — correct.
  - `slugify`: `s.strip().lower()` then `re.sub(r"\s+", "-", ...)` correctly handles leading/trailing whitespace, lowercasing, and collapsing any whitespace run (spaces, tabs, newlines) to a single hyphen. Matches `"Hello World" → "hello-world"` and `"  A  B  " → "a-b"`.
  - `re` is stdlib — no dependency violation.

## Evidence Check
- Diff shows only `scripts/harness_demo.py` created (new file, 16 lines). No other files touched.
- Test output: `14 passed in 0.03s` — all tests pass, consistent with acceptance criterion.
- No guardrail violations reported.
- Test file `tests/test_harness_demo.py` not modified.

## Scope Drift Check
- No scope drift. Only the single allowed file (`scripts/harness_demo.py`) was created. No dependency changes, no package installs, no destructive actions, no test file modifications.

## Test Coverage Check
- All 14 tests pass per the evidence. Functions are low-risk (pure arithmetic / string manipulation), and the regex approach in `slugify` is robust to multiple whitespace types, which likely explains why all 14 tests pass.
- Specific acceptance cases verified mentally:
  - `add(2, 3) == 5` ✓
  - `add(-1, 1) == 0` ✓
  - `is_even(4) is True` ✓
  - `is_even(7) is False` ✓
  - `slugify("Hello World") == "hello-world"` ✓
  - `slugify("  A  B  ") == "a-b"` ✓

## Recommended Next Action
Merge / close ticket. No revision needed.

## Known Failures / Exceptions

Test passed: True
Guardrail violations: None
Escalation notes: None

## Request to Opus

Approve, request revision, or reject this patch. Identify blocking issues and required revisions.
