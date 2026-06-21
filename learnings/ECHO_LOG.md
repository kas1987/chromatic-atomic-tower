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

## Sprint 012 / MP-CAT-A012-4C01 (2026-06-18)

- **`BEAD_GLOB_PATTERNS` must include `beads/queued/`.** GO pipeline plan_decompose was blind to queued BEADs; add the folder to the front of `cat_align_common.py` `BEAD_GLOB_PATTERNS` whenever a new lifecycle folder is introduced.
- **`beads: []` in mission contracts.** Never put BEAD IDs in the `beads:` array — schema expects objects; IDs live in separate BEAD YAML files.
- **Reconciliation target requires sprint-close update.** Add the closed mission to `required_missions` and clear `canonical_active_mission_id` in `LIVE_REPO_ALIGNMENT_TARGET.yaml`; failing this breaks `test_reconciliation_passes` and `test_registry_audit_passes`.
- **Closeout backslash bug.** `cat_sprint_closeout.py` writes `missions\archived\...` (backslash) on Windows; fix with `path.as_posix()` before writing path into the registry YAML. Low-severity but should be patched.
- **Next sprint:** Tower is `sprint_idle` — no backlog missions remain. G-8 (live DB/comms integration) requires a new security-gated mission kickoff.

## Sprint 013 / PR #40 review-response learnings

- **Rollback integration tests are missing.** Existing tests cover happy-path transitions but not rollback scenarios: (a) rollback after `--move` terminal transition, (b) rollback after non-terminal transition, (c) rapid-succession rollback. Four sequential P1 rollback bugs were caught by AI reviewers, not tests.
- **`sprint_idle` skip in enforcement scripts is by design.** Governance PRs (retros, conformance, structural fixes) are legitimate during idle state; fail-closed would block them. Document skip reason explicitly in the stderr message.
- **Stale mission files cause `MISSION_ID_COLLISION`.** Before merging any PR touching `missions/`, run `pytest tests/test_state_freshness.py -k test_live_repo_is_fresh` locally.
- **YAML list items should be indented 2 spaces under their key**, not at the same level — the at-level form is valid per spec but flagged by Copilot as invalid.

## Sprint 013 / coverage-80pct spike (2026-06-18)

- **Dual-namespace test imports corrupt real files.** Any test that mixes `import cat_foo as mod` with `from scripts.cat_foo import func` risks patching the wrong namespace and writing to real repo state. CI caught it as a repeating `scorecard_parity` failure. Enforce single-namespace pattern in PR review.
- **`.coverage` must be in root allowlist.** First coverage PR will always hit `schema_validation FAIL` unless `.coverage` is added to `gates/hygiene/root_allowlist.yaml` `ignored_entries` upfront. Make this part of the "add pytest-cov" checklist.
- **Coverage target 80 % reached — do not let it regress.** `pyproject.toml` `--cov-fail-under=55` is a stale floor; update to `80` to protect the new baseline.
- **Rollback integration tests still missing** — carried from Sprint 013. Next test sprint should prioritise this.
