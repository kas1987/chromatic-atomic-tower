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
