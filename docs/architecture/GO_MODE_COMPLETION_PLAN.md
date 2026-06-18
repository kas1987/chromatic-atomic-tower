# GO-Mode Completion Plan — closing the Chromatic Atomic Harness gaps

**Owner:** Orchestrator (Opus) · **Implementers:** Sonnet subagents
**Target:** [CHROMATIC_ATOMIC_HARNESS_CONFORMANCE.md](CHROMATIC_ATOMIC_HARNESS_CONFORMANCE.md)

This plan sequences the remaining gap backlog into parallelizable units and one
serial design effort (G-1a). It is the program-level view of "build to this".

## Parallel workstreams (Sonnet agents, disjoint file ownership)

| Gap | Deliverable | Owns (new files only) |
|-----|-------------|-----------------------|
| **G-2** | Intent envelope schema — normalizes pipeline stage 1 (Intent) | `schemas/intent_envelope.schema.json`, `tests/fixtures/intent/*`, `tests/test_intent_envelope.py` |
| **G-3** | Handoff packet schema — structures the Orchestrator-layer Handoff | `schemas/handoff_packet.schema.json`, `tests/fixtures/handoff/*`, `tests/test_handoff_packet.py` |
| **G-4** | Mission Package artifact — the diagram's review-ready output bundle | `scripts/cat_mission_package.py`, `schemas/mission_package.schema.json`, `tests/test_mission_package.py` |
| **G-1a** | Active GO-mode orchestrator — *advances* a mission stage-by-stage | `scripts/cat_go_run.py`, `tests/test_go_run.py` |

**Invariants for every agent:** create only the listed files; edit no existing
file; run no git; validate only the new test file. Integration into shared
files (`cat_validate.py` VALIDATION_TARGETS, `cat_ci.py`, the conformance map,
`schemas/README.md`) and all commits are performed by the Orchestrator.

## G-1a design contract (active orchestrator)

The read-only spine (`cat_go.py`) reports stage status. `cat_go_run.py` adds the
*advance* capability under strict safety rules:

1. **Default dry-run.** Prints the next actionable stage + planned action +
   `go_run_record`; mutates nothing.
2. **Delegation, not direct mutation.** `--execute` performs only safe,
   automatable transitions by invoking existing **audited** scripts
   (`cat_sprint_closeout.py`, `cat_transition.py`) via subprocess — it never
   writes tower/registry/BEAD state directly.
3. **Confidence + human gate.** If the confidence band is `self_heal` or
   `escalate_or_block`, or the action is a mission close, `--execute` refuses
   and prints a human-approval notice (No Gate = No Promotion).
4. **Auditable.** Emits a `go_run_record` (reusing `cat_go.evaluate`) plus the
   chosen `next_action` under `evidence/go/`.

## Integration & sequencing (Orchestrator)

1. Collect agent outputs; run the **full** suite; fix any cross-file issues.
2. Wire the three new schemas into `cat_validate.py` validation targets.
3. Update the conformance map: move G-2/G-3/G-4/G-1a to "Recently closed".
4. Commit each workstream as a logical unit; push; verify CI green.
5. Surface G-1a `--execute` to the Human Owner for first live use (human gate).

## Out of scope this pass

Calendar/Email tool plane, first-class Database plane (G-7+), and any change to
master (PR #27 merge remains the Human Owner's action).
