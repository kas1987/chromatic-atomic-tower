# Learning Record: MP-CAT-A007-4C01 LOGHOUSE

**Mission**: MP-CAT-A007-4C01 — LOGHOUSE Log Intelligence and Architecture Drift MVP  
**Status**: Complete (all 8 BEADs closed; mission archived 2026-06-18)  
**Recorded**: 2026-06-17 (updated 2026-06-18)

---

## Decisions

### D-001: Adopt Phase-1 LOGHOUSE schemas as baseline
Rather than redesigning the telemetry_envelope, finding, dependency_edge, and deploy_event
schemas, Wave 1 adopted the pre-existing Phase-1 contracts and extended them with three new
schemas (dispatch_queue_item, architecture_rule, drift_report). This avoided schema churn and
kept backward compatibility with existing tests.

### D-002: Evidence-first is a hard constraint, not a convention
The findings engine was implemented to reject any finding that lacks at least one evidence
item. This is enforced in `build_finding()` with a ValueError, not just a schema check. The
design makes it impossible for a rule to emit an unevidenced finding without explicitly
crashing the pipeline.

### D-003: Deterministic IDs for golden tests
Golden test fixtures use hardcoded UUIDs (e.g., `f1111111-...`, `d1111111-...`) to ensure
test determinism. The engine always accepts an explicit `finding_id`/`dispatch_id` parameter,
so production runs generate random UUIDs while tests use stable goldens.

### D-004: CLI defaults to OS temp dir to prevent root pollution
Wave 1 originally wrote output to a root-level `output/` directory. This violated root
hygiene (the allowlist does not include `output/`). The fix was to default `--output` to
`Path(tempfile.gettempdir()) / "loghouse"`. CI passes `--output /tmp/loghouse_ci_output`
explicitly.

### D-005: Drift gate is a standalone script, not inlined in CI
The drift gate (`scripts/loghouse/drift_gate.py`) is a reusable CLI that can be invoked
both from the Makefile (`make loghouse-gate`) and from CI. Inlining the logic in the YAML
workflow would make it untestable locally.

### D-006: Agent-drift findings use category "aiops"
The finding schema enum is `["reliability", "performance", "security", "drift", "governance", "aiops"]`.
Agent-drift findings were mapped to `"aiops"` rather than creating a new category value, to
avoid modifying the finding schema (which would break existing validated records).

### D-007: Clean fixture for CI "must pass" gate step
The drift gate CI step tests both directions: the standard fixture has a P0 blocked edge
(frontend → database), which must fail the gate. A separate `dependency_edges_clean.json`
fixture with only allowed edges is used to prove the gate passes when no violations are present.

---

## What Worked

- **Layered architecture** (normalize → correlate → rules → findings → dispatch) made each
  layer independently testable and replaceable.
- **Schema-gating at every layer** (via `validate_with_schema`) caught integration errors
  early and produced clear error messages.
- **Pytest fixture-driven approach** with `tests/fixtures/loghouse/` gave a stable, repeatable
  end-to-end smoke test that runs in under 2 seconds.
- **Common helpers** (`scripts/common.py`) made it trivial to reuse ROOT detection,
  schema validation, and YAML loading across all engine modules.
- **Makefile `loghouse` target** bridges CI and local development: the same checks run in
  both environments without environment-specific scripts.

---

## Risks

### R-001: Rule set is static YAML
Architecture rules are currently static. If rules change frequently, the static YAML becomes
a maintenance burden. A future iteration could read rules from the dependency graph dynamically.

### R-002: Agent observability is trace-in, not live-hook
`agent_obs.py` processes a trace dict post-hoc. It does not hook into live agent execution.
Real-time observability would require integration with the agent harness event loop.

### R-003: No deduplication of findings across runs
If the pipeline is run twice on the same fixtures, it will produce duplicate findings with
different UUIDs. A future iteration should deduplicate by (rule_id, service, deploy_id, window).

### R-004: Drift gate only covers fixture edges
The CI drift gate runs against `tests/fixtures/loghouse/dependency_edges.json`. In a production
setup, the edges would need to be extracted from a live graph snapshot. The gate script accepts
a `--edges` argument to support this, but the extraction step is out of scope for this MVP.

---

## Follow-Ups

- [ ] FU-001: Add deduplication logic to the findings engine (key = rule_id + service + deploy_id).
- [ ] FU-002: Implement live agent hook integration in `agent_obs.py` via harness event loop.
- [ ] FU-003: Add a dependency graph extraction script that produces `dependency_edges.json`
       from the live repo state (e.g., import graph scanning).
- [ ] FU-004: Extend `drift_gate.py` to accept multiple edge files or a directory.
- [ ] FU-005: Consider promoting the `loghouse` Makefile target to the standard `make check`
       composite so LOGHOUSE checks always run with the repo health suite.
- [ ] FU-006: Add Prometheus/OpenTelemetry metric emission stubs to `normalize.py` so the
       engine can feed a live metrics backend when one is available.

---

## Mission-Level Metrics (at Wave 2 close)

| Metric | Result |
|---|---|
| Schemas (7) | All present, valid JSON Schema, tested valid+invalid |
| Engine modules | 6 modules import cleanly |
| Pytest tests | 143 (Wave 1) + new BEAD-07 tests; all green |
| Findings from fixture | >= 3 (error-spike, exception-explosion, forbidden-edge) |
| Dispatch items | >= 3 (one per finding) |
| Drift: blocked edges | 1 (frontend → database, RULE-002, P0) |
| CI workflow | cat-loghouse-ci.yml — 8 steps, no secrets, no network |
| Mermaid diagrams | 3 (architecture-flow, findings-lifecycle, drift-detection-flow) |
| Runbooks | 2 (incident-to-finding, drift-review) |
| Dispatch board | 1 (LOGHOUSE_DISPATCH_BOARD.md) |
