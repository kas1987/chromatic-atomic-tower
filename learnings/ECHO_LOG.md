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

## Sprint 005 / Session 2026-06-18

- **Mission must be dispatched before BEAD-001 activates.** MP-CAT-005 is stuck at `approved` because BEAD-001 was activated directly. Next sprint: check mission status before activating any BEAD, or add an all-BEADs-complete bypass in the state machine.
- **`cat_transition.py` now emits `''` not `null` for `active_bead_id`.** Schema-valid after BEAD closeout. Apply same pattern to any new nullable tower-state fields.
- **Gitignore test fixture closeout reports.** `BEAD-CAT-*-CLOSEOUT-EXAMPLE_closeout_*.md` and `BEAD-CAT-DOES-NOT-MATCH_closeout_*.md` accumulate per pytest run; add `.gitignore` patterns before next sprint.
- **Session-start branch snapshot is untrustworthy.** Always run `git branch --show-current` before committing — the `gitStatus` injection can be stale when a concurrent writer switched branches between session open and first tool call.
