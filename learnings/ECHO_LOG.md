# Echo Log

The Echo Log records what the system should remember next time.

## Sprint 000 seed learning

- CAT should remain a control system, not a general knowledge base.
- V2 should be mined selectively, not copied wholesale.
- `GO` must resolve to a BEAD, not an open-ended agent instruction.

## Sprint 004 / MP-CAT-A006 learning (2026-06-17)

- `bd remember` and `learnings/` are separate stores; `/post-mortem` must write to both.
- Multi-agent sessions need an explicit quiet-check before any branch switch.
- Closing a VS Code window does not stop a running Copilot agent.

## Sprint 009 / MP-CAT-A009-4C01 (2026-06-18)

- **Donor zip ≠ live lineage.** Sprint 004 zip used `MP-CAT-004` for reconciliation; live repo had V2 Alignment on that ID. Always remap to new A-tier ID before scaffold.
- **Mission `approved`, BEAD `active`.** Mission contracts must not use `status: active`; it fails schema validation.
- **Closeout updates reconciliation target.** Set `canonical_active_mission_id: ''` and `MP-CAT-A009-4C01: closed` in target YAML when running sprint closeout.
- **Next sprint:** `MP-CAT-A010-4C01` GitHub Bridge — verify `beads/active/` has no duplicate A010 contracts before dispatch.

- **`cat_transition.py` now emits `''` not `null` for `active_bead_id`.** Schema-valid after BEAD closeout. Apply same pattern to any new nullable tower-state fields.
- **Gitignore test fixture closeout reports.** `BEAD-CAT-*-CLOSEOUT-EXAMPLE_closeout_*.md` and `BEAD-CAT-DOES-NOT-MATCH_closeout_*.md` accumulate per pytest run; add `.gitignore` patterns before next sprint.
- **Session-start branch snapshot is untrustworthy.** Always run `git branch --show-current` before committing — the `gitStatus` injection can be stale when a concurrent writer switched branches between session open and first tool call.

## Sprint 010 / MP-CAT-A010-4C01 (2026-06-18)

- **Donor zip sprint numbers ≠ live repo IDs.** `chromatic_atomic_tower_sprint_005.zip` mapped to live Sprint 010 / `MP-CAT-A010-4C01`. Always reconcile against `LIVE_REPO_ALIGNMENT_TARGET.yaml` before assigning mission IDs from a donor package.
- **GitHub Bridge validators need dual ID regex.** Legacy `[MP-CAT-###]` and A-tier `[MP-CAT-A010-4C01]` patterns must both pass; donor-only legacy regex breaks new-work policy.
- **Post-closeout tests must use `beads/completed/`.** Hardcoded `beads/active/` paths fail after transition engine moves contracts.
- **Next sprint:** `MP-CAT-A011-4C01` Agent Scorecard Automation — expand backlog scaffold before GO.
