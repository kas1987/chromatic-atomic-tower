```markdown
# Cheap Review

## Decision
APPROVE

## Findings
- `scripts/cat_stats.py`: Clean implementation using only stdlib (`argparse`, `glob`, `json`, `os`, `sys`, `typing`) and `yaml` (PyYAML) as required. ✓
- `scripts/cat_stats.py:13-15`: `_repo_root()` correctly resolves the parent of the `scripts/` directory via `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`. ✓
- `scripts/cat_stats.py:18-21`: Uses `yaml.safe_load` (not `yaml.load`), which is the correct security-conscious choice. ✓
- `scripts/cat_stats.py:33-38`: `_count_by_status` skips items with `status is None`, handling malformed entries gracefully.
- `scripts/cat_stats.py:48-72`: `summarize()` defensively handles missing `missions` key (`or []`), missing registry (`FileNotFoundError`), missing beads directory (silently empty), and malformed bead YAMLs (`yaml.YAMLError` caught). Filters beads to those containing both `bead_id` and `status`, consistent with the ticket's "at minimum" requirement.
- `scripts/cat_stats.py:75-94`: `main()` implements `--json` flag, defaults to human-readable output, and returns proper exit codes (1 on missing registry).
- Minor: `total_missions` uses `len(missions)` while `missions_by_status` only counts entries with a status, so the two can differ if a mission lacks a `status` key. This is acceptable since the acceptance criteria don't require equality and it matches the ticket's specified return keys.

## Evidence Check
- Test output provided: `12 passed in 0.38s` — matches ticket expectation (`tests/test_cat_stats.py`).
- Test result flag: `Test Passed: True`.
- Guardrail violations: `[]` (empty).
- The required command `python -m pytest -q tests/test_cat_stats.py` is implied by the test run; results confirm it succeeds.
- No worker claims about file existence are unverified — the diff shows the new file was created and test execution succeeded.

## Scope Drift Check
- Files written: only `scripts/cat_stats.py` (per `Files Written` and `Diff`). ✓
- No YAML files modified. ✓
- No new dependencies installed. ✓
- No third-party imports beyond PyYAML. ✓

## Test Coverage Check
- 12 tests pass with no reported skips or warnings.
- The acceptance criteria (`active_mission_id == "MP-CAT-000"`, `"approved"` in `missions_by_status`, `total_missions >= 3`, `total_active_beads >= 4`, JSON output validity, `summarize()` key set) are all exercised by the passing test suite.

## Recommended Next Action
Merge the patch. The implementation is minimal, correct, matches all ticket requirements, passes tests, and introduces no scope drift or dependency changes.
```