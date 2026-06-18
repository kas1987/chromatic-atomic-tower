# LOGHOUSE Self-Observability Design

**Date:** 2026-06-17
**Branch:** mp-cat-007-log-intelligence
**Sprint:** SPRINT-008
**Author:** Human Owner + Claude

---

## Problem

CAT emits rich operational events — BEAD transitions, evidence gate outcomes, GO decisions, agent session metadata — but nothing consumes them. LOGHOUSE was built for external service telemetry (OTel/Vector intake) but its pipeline can serve CAT's own governance observability. The goal is to wire CAT's own activity into LOGHOUSE so governance anomalies surface as evidence-backed findings that gate CI and block GO.

---

## Approach

**Thin adapter layer (Approach A).** A `cat_adapter.py` reads CAT's existing JSONL logs and maps them into `telemetry_envelope` records. These feed directly into the existing normalize → correlate → rules → findings → dispatch pipeline. Four new CAT-specific rules are added to `rules.py`. Critical findings (P0/P1) block `cat_resolve_go.py` and fail CI. Findings go to the dispatch board.

Rejected approaches:
- **Parallel governance monitor** — two anomaly systems in one repo; loses evidence-first architecture.
- **New governance signal schema** — adds an 8th schema to A007's complete set; over-engineering for current need.

---

## Architecture

```
CAT operational logs              Adapter              Existing LOGHOUSE pipeline
─────────────────────             ───────              ──────────────────────────
evidence/transitions/             cat_adapter.py  ──▶  normalize → correlate → rules → findings → dispatch
  transition_log.jsonl       ──▶   (maps to              ↑ 4 new CAT-specific rules
evidence/logs/                     telemetry_            
  closeouts.jsonl            ──▶   envelope)     
  go_decisions.jsonl (new)   ──▶
  AGENT_RUN_LOG.jsonl (new)  ──▶
                                                        findings
                                                           │
                                                  ┌────────┴────────┐
                                                  ▼                 ▼
                                         dispatch board         CI gate / GO block
                                       (LOGHOUSE_DISPATCH_   (cat_resolve_go.py +
                                        BOARD.md updated)     cat-loghouse-ci.yml)
```

### telemetry_envelope field mapping convention

| `telemetry_envelope` field | CAT governance meaning |
|---|---|
| `service` | `"cat"` |
| `env` | `"local"` or `"ci"` |
| `signal_type` | `"bead_transition"` / `"closeout"` / `"go_decision"` / `"agent_run"` |
| `commit_sha` | `git rev-parse HEAD` at time of event |
| `deploy_id` | `active_sprint` from `TOWER_STATE.yaml` (e.g. `"SPRINT-008"`) |

These are governance conventions, not CI deployment fields. Documented in `cat_adapter.py` docstring.

---

## New Files

| File | Purpose |
|---|---|
| `scripts/loghouse/cat_adapter.py` | Reads CAT JSONL logs → `telemetry_envelope` records |
| `scripts/cat_run_log.py` | CLI writer for `AGENT_RUN_LOG.jsonl` — called at session end |
| `evidence/logs/go_decisions.jsonl` | New log — appended by `cat_resolve_go.py` on every GO run |
| `evidence/logs/AGENT_RUN_LOG.jsonl` | New log — session agent metadata (harness-v2 schema) |
| `tests/fixtures/loghouse/cat_self_signals.json` | Golden fixture for adapter + self-monitor pipeline |
| `tests/test_loghouse_self_monitor.py` | Tests for adapter, new rules, self-monitor mode |
| `docs/superpowers/specs/2026-06-17-loghouse-self-observability-design.md` | This file |

## Modified Files

| File | Change |
|---|---|
| `scripts/loghouse/normalize.py` | Extend `VALID_SIGNAL_TYPES` and `VALID_ENVS` |
| `schemas/telemetry_envelope.schema.json` | Update `enum` arrays to match |
| `scripts/loghouse/rules.py` | Add 4 CAT governance rules |
| `scripts/cat_loghouse.py` | Add `--mode self` flag |
| `scripts/cat_resolve_go.py` | Append GO decision; call LOGHOUSE at end; block on P0/P1 |
| `docs/operations/LOGHOUSE_DISPATCH_BOARD.md` | Add routing rows for 4 new rules |
| `.github/workflows/cat-loghouse-ci.yml` | Add self-monitoring CI job |

---

## Schema Extensions

`scripts/loghouse/normalize.py` — extend constants:

```python
VALID_SIGNAL_TYPES = {
    "log", "metric", "trace", "event",
    # CAT governance signals
    "bead_transition", "closeout", "go_decision", "agent_run",
}

VALID_ENVS = {
    "dev", "staging", "prod",
    # CAT local and CI environments
    "local", "ci",
}
```

`schemas/telemetry_envelope.schema.json` — update `signal_type` and `env` enum arrays to match.

---

## AGENT_RUN_LOG Schema

Matches harness-v2 `07_LOGS_AND_AUDIT/AGENT_RUN_LOG.jsonl` pattern:

```json
{
  "task_id": "BEAD-CAT-A007-4C01-03",
  "model": "claude-sonnet-4-6",
  "role": "worker",
  "confidence_score": 85.0,
  "risk_level": "medium",
  "tools_used": 12,
  "files_touched": ["scripts/loghouse/normalize.py", "tests/test_loghouse_engine.py"],
  "result": "normalizer extended, tests passing",
  "validation": "pytest -q passed",
  "next_task": "BEAD-CAT-A007-4C01-04"
}
```

`cat_run_log.py` CLI:
```bash
python scripts/cat_run_log.py \
  --confidence 85 \
  --result "closed BEAD-CAT-A007-01" \
  --files "scripts/loghouse/normalize.py,tests/test_loghouse_engine.py" \
  --validation "pytest -q passed" \
  --next-task "BEAD-CAT-A007-4C01-04"
```

Reads `active_bead_id` and `active_sprint` from `state/TOWER_STATE.yaml`. Reads `git rev-parse HEAD` for `commit_sha`. Writes one JSON line to `evidence/logs/AGENT_RUN_LOG.jsonl`.

---

## GO Decision Log Schema

`evidence/logs/go_decisions.jsonl` — one record per `cat_resolve_go.py` run:

```json
{
  "ts": "2026-06-18T01:00:00+00:00",
  "allowed": false,
  "drift_count": 1,
  "drifts": ["MISSION_ID_COLLISION"],
  "sprint": "SPRINT-008",
  "commit_sha": "a6aec4f2"
}
```

---

## New Rules

All four rules operate on `CorrelationWindow` objects (keyed by `sprint_id`/`commit_sha`/`service="cat"`).

### 1. `bead-stuck-in-state`

**Trigger:** A BEAD has been in `in_progress` or `validating` for more than 24h with no subsequent transition.

**Severity:**
- P2 if 24h ≤ elapsed < 48h (dispatch only)
- P1 if elapsed ≥ 48h (blocks GO + CI)

**Evidence:** The `bead_transition` envelope that entered the stuck state + elapsed-time calculation.

**Owner:** AUDITOR

---

### 2. `go-block-frequency`

**Trigger:** GO blocked ≥3 times within any 1-hour window of `go_decision` envelopes.

**Severity:**
- P1 if 3–4 blocks (blocks GO + CI)
- P0 if ≥5 blocks (blocks GO + CI, critical escalation)

**Evidence:** The `go_decision` envelope records showing `allowed=false` + drift reasons.

**Owner:** AUDITOR

---

### 3. `closeout-rejection-spike`

**Trigger:** ≥50% of `closeout` envelopes in a 2-hour window have `allowed=false`.

**Severity:**
- P2 if 50–79% rejected (dispatch only)
- P0 if ≥80% rejected (blocks GO + CI)

**Evidence:** Closeout envelope records with `allowed=false` + rejection reasons.

**Owner:** REVIEWER

---

### 4. `confidence-below-threshold`

**Trigger:** An `agent_run` envelope has `confidence_score` below 70 (CAT's `confidence_minimum`).

**Severity:** P2 (dispatch only — never blocks GO alone).

**Evidence:** The `agent_run` envelope record.

**Owner:** REVIEWER

---

## Dispatch Board Routing

New rows added to `docs/operations/LOGHOUSE_DISPATCH_BOARD.md`:

| Rule | Category | Severity | Agent Role | Rationale |
|---|---|---|---|---|
| `bead-stuck-in-state` | governance | P2→P1 | AUDITOR | Governance stall; operator triage required |
| `go-block-frequency` | governance | P1→P0 | AUDITOR | Systematic GO failure; escalate immediately |
| `closeout-rejection-spike` | governance | P2→P0 | REVIEWER | Evidence quality problem; review before more submissions |
| `confidence-below-threshold` | governance | P2 | REVIEWER | Low-confidence run; review output before accepting |

---

## Data Flow — `cat_resolve_go.py` Run

```
1. cat_resolve_go.py runs existing drift checks
2. Appends GO decision record → evidence/logs/go_decisions.jsonl
3. Calls cat_loghouse.py --mode self
     cat_adapter.py reads:
       evidence/transitions/transition_log.jsonl
       evidence/logs/closeouts.jsonl
       evidence/logs/go_decisions.jsonl
       evidence/logs/AGENT_RUN_LOG.jsonl
     → normalize (with extended signal_types and envs)
     → correlate (window key: service="cat", env="local", sprint_id, git HEAD)
     → rules (4 new CAT rules; existing service rules no-op on "cat" service windows)
     → findings (evidence-first; each finding links to source JSONL line + offset)
     → dispatch (emit dispatch_queue_items; update LOGHOUSE_DISPATCH_BOARD.md)
4. cat_loghouse.py exits non-zero if any P0 or P1 finding emitted
5. cat_resolve_go.py: if exit code != 0 → print findings → block GO
   If exit code == 0 → GO proceeds normally
```

---

## CI Job

Added to `.github/workflows/cat-loghouse-ci.yml`:

```yaml
- name: LOGHOUSE self-monitor
  run: python scripts/cat_loghouse.py --mode self --strict
  # --strict: exits non-zero on any P0/P1 finding
  # Runs on every push; findings from CI use env="ci"
```

---

## `--mode self` Flag in `cat_loghouse.py`

```bash
# External service mode (existing, uses fixture dir):
python scripts/cat_loghouse.py --input tests/fixtures/loghouse --output /tmp/loghouse/output

# Self-monitoring mode (new):
python scripts/cat_loghouse.py --mode self [--strict] [--output /tmp/loghouse/self]
```

`--mode self` skips the `--input` fixture loading and calls `cat_adapter.py` instead. `--strict` makes the CLI exit non-zero on any P0/P1 finding (used in CI and GO integration).

---

## Testing

| Test file | Coverage |
|---|---|
| `tests/test_loghouse_self_monitor.py` | adapter round-trip, each new rule fires correctly, each new rule suppresses correctly, `--mode self` end-to-end |
| `tests/fixtures/loghouse/cat_self_signals.json` | Golden fixture with representative signals for all 4 rule types |

Existing test files are not modified.

---

## Success Criteria

- `python scripts/cat_loghouse.py --mode self` runs without error on a clean repo state.
- `pytest -q tests/test_loghouse_self_monitor.py` passes.
- `cat_resolve_go.py` appends a `go_decisions.jsonl` entry on every run.
- `cat_run_log.py --confidence 85 --result "test"` writes a valid line to `AGENT_RUN_LOG.jsonl`.
- Injecting a stuck BEAD into the fixture causes `bead-stuck-in-state` to fire.
- Injecting 5 blocked GO decisions causes `go-block-frequency` (P0) to fire and block GO.
- `cat-loghouse-ci.yml` self-monitor job passes on a clean fixture.
- `LOGHOUSE_DISPATCH_BOARD.md` shows all 4 new rules in the routing table.

---

## Out of Scope

- Standing up OTel Collector or Vector against real services.
- Auto-remediation or auto-created PRs from findings.
- Backfilling historical JSONL logs into LOGHOUSE.
- Changes to any Sprint 000–005 mission files or beads.
