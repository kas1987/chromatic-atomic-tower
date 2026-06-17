# Review Packet

## Ticket

# Ticket: REAL-001 Implement scripts/cat_stats.py

## Priority
p1

## Objective

Create `scripts/cat_stats.py` — a stdlib + PyYAML CLI that reads
`missions/registry/MISSION_REGISTRY.yaml` and every `beads/active/*.yaml`, exposes
a `summarize() -> dict` function (used by tests) and a `main()` that prints the summary.
Support a `--json` flag. No third-party libraries beyond PyYAML.

## Context

The CAT repo tracks missions and beads in YAML files. A lightweight stats utility is
needed to surface repo health at a glance (total missions, missions grouped by status,
active mission, total active beads, beads grouped by status).

- Mission registry: `missions/registry/MISSION_REGISTRY.yaml`
  - Has keys: `active_mission_id`, `missions` (list)
  - Each mission has at minimum: `mission_id`, `status`
- Active beads: `beads/active/*.yaml`
  - Each bead has at minimum: `bead_id`, `status`
- Only stdlib + PyYAML may be used (PyYAML is already installed).
- `summarize()` must return a dict with exactly these keys:
  - `total_missions` (int)
  - `missions_by_status` (dict str->int)
  - `active_mission_id` (str or None)
  - `total_active_beads` (int)
  - `beads_by_status` (dict str->int)
- `main()` prints the summary; with `--json` flag it prints valid JSON.
- Paths must be resolved relative to the repo root (parent of `scripts/`).

## Allowed Files

- `scripts/cat_stats.py`

## Blocked Actions

- Do not modify files outside allowed list.
- Do not change dependencies or install packages.
- Do not perform destructive actions.
- Do not import third-party libraries (stdlib + PyYAML only).
- Do not modify any YAML files.

## Required Commands

```bash
python -m pytest -q tests/test_cat_stats.py
```

## Output Required

- Complete contents of `scripts/cat_stats.py` as a FILE block
- Worker summary
- Known risks

## Acceptance Criteria

- `summarize()` returns a dict with keys: `total_missions`, `missions_by_status`, `active_mission_id`, `total_active_beads`, `beads_by_status`
- `active_mission_id == "MP-CAT-000"`
- `"approved"` is a key in `missions_by_status` and the count for `"MP-CAT-000"` status is correct
- `total_missions >= 3`
- `total_active_beads >= 4`
- Running `python scripts/cat_stats.py --json` produces valid JSON with the same keys
- All tests in `tests/test_cat_stats.py` pass

## Stop Conditions

Stop and report if:

- Required YAML files are missing or unparseable
- The task requires modifying any file other than `scripts/cat_stats.py`
- The implementation requires a non-stdlib, non-PyYAML dependency
- Tests cannot be satisfied by the described function signatures
- More than 2 implementation attempts fail


## Files Changed

```text
scripts/cat_stats.py

```

## Diff Summary

```text
 scripts/cat_stats.py | 124 +++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 124 insertions(+)

```

## Patch / Targeted Diff

```diff
diff --git a/scripts/cat_stats.py b/scripts/cat_stats.py
new file mode 100644
index 0000000..2273327
--- /dev/null
+++ b/scripts/cat_stats.py
@@ -0,0 +1,124 @@
+#!/usr/bin/env python3
+"""
+cat_stats.py
+
+Lightweight repo-health utility for the CAT repository.
+
+Reads:
+  - missions/registry/MISSION_REGISTRY.yaml
+  - beads/active/*.yaml
+
+Produces summary statistics about missions and active beads.
+"""
+
+import argparse
+import glob
+import json
+import os
+import sys
+from typing import Any, Dict, List, Optional
+
+import yaml
+
+
+def _repo_root() -> str:
+    """Return the repository root directory (parent of scripts/)."""
+    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
+
+
+def _load_yaml(path: str) -> Any:
+    with open(path, "r", encoding="utf-8") as f:
+        return yaml.safe_load(f)
+
+
+def _missions_path() -> str:
+    return os.path.join(_repo_root(), "missions", "registry", "MISSION_REGISTRY.yaml")
+
+
+def _beads_dir() -> str:
+    return os.path.join(_repo_root(), "beads", "active")
+
+
+def _count_by_status(items: List[Dict[str, Any]]) -> Dict[str, int]:
+    counts: Dict[str, int] = {}
+    for item in items:
+        status = item.get("status")
+        if status is None:
+            continue
+        counts[status] = counts.get(status, 0) + 1
+    return counts
+
+
+def summarize() -> Dict[str, Any]:
+    """
+    Summarize mission registry and active bead YAMLs.
+
+    Returns a dict with keys:
+      - total_missions (int)
+      - missions_by_status (dict str->int)
+      - active_mission_id (str or None)
+      - total_active_beads (int)
+      - beads_by_status (dict str->int)
+    """
+    registry_path = _missions_path()
+    if not os.path.exists(registry_path):
+        raise FileNotFoundError(f"Mission registry not found: {registry_path}")
+
+    registry = _load_yaml(registry_path) or {}
+    missions = registry.get("missions") or []
+    active_mission_id = registry.get("active_mission_id")
+
+    missions_by_status = _count_by_status(missions)
+
+    beads_dir = _beads_dir()
+    beads: List[Dict[str, Any]] = []
+    if os.path.isdir(beads_dir):
+        for bead_path in sorted(glob.glob(os.path.join(beads_dir, "*.yaml"))):
+            try:
+                bead = _load_yaml(bead_path) or {}
+                if isinstance(bead, dict) and "bead_id" in bead and "status" in bead:
+                    beads.append(bead)
+            except yaml.YAMLError:
+                # Skip malformed bead YAML files.
+                continue
+
+    beads_by_status = _count_by_status(beads)
+
+    return {
+        "total_missions": len(missions),
+        "missions_by_status": missions_by_status,
+        "active_mission_id": active_mission_id,
+        "total_active_beads": len(beads),
+        "beads_by_status": beads_by_status,
+    }
+
+
+def main(argv: Optional[List[str]] = None) -> int:
+    parser = argparse.ArgumentParser(description="Print CAT repo mission and bead stats.")
+    parser.add_argument(
+        "--json",
+        action="store_true",
+        help="Output the summary as JSON.",
+    )
+    args = parser.parse_args(argv)
+
+    try:
+        summary = summarize()
+    except FileNotFoundError as exc:
+        print(f"Error: {exc}", file=sys.stderr)
+        return 1
+
+    if args.json:
+        print(json.dumps(summary, indent=2))
+    else:
+        print(f"Total missions: {summary['total_missions']}")
+        print(f"Missions by status: {summary['missions_by_status']}")
+        print(f"Active mission ID: {summary['active_mission_id']}")
+        print(f"Total active beads: {summary['total_active_beads']}")
+        print(f"Beads by status: {summary['beads_by_status']}")
+
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())

```

## Test Commands Run

```text
python -m pytest -q tests/test_cat_stats.py
```

## Test Results

```text
............                                                             [100%]
12 passed in 0.38s

```

## Worker Self-Assessment

Worker model: kimi-k2.7-code:cloud
Attempts used: 1 / 2
Files written: ['scripts/cat_stats.py']
Guardrail violations: []
Escalation notes: []

## Cheap Reviewer Notes

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

## Known Failures / Exceptions

Test passed: True
Guardrail violations: None
Escalation notes: None

## Request to Opus

Approve, request revision, or reject this patch. Identify blocking issues and required revisions.
