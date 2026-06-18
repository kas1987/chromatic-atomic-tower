# Runbook: Incident to Finding

**System**: LOGHOUSE Log Intelligence  
**Mission**: MP-CAT-A007-4C01  
**Audience**: CAT Operators, On-Call Agents

---

## Purpose

This runbook describes how to take a raw incident signal (log spike, deploy failure,
dependency violation) and produce an evidence-backed LOGHOUSE finding that routes to the
correct CAT agent role via the dispatch board.

---

## Prerequisites

- Repo at C:\.01_CAT (or `$CAT_ROOT`) checked out on the working branch.
- Python environment with `requirements.txt` installed.
- Input signals in `tests/fixtures/loghouse/raw_signals.json` (or your custom input dir).

---

## Step 1 — Collect and stage raw signals

Place raw signal records in a directory accessible to the LOGHOUSE CLI.  
Each record must include at minimum: `service`, `env`, `signal_type`, `ts`, `commit_sha`,
`deploy_id`.

For deploy events also include: `actor`, `started_at`, `completed_at`, `status`.

**Example** (using the standard fixture):

```
tests/fixtures/loghouse/raw_signals.json
tests/fixtures/loghouse/dependency_edges.json  (optional)
```

---

## Step 2 — Run the LOGHOUSE pipeline

```bash
python scripts/cat_loghouse.py \
  --input tests/fixtures/loghouse \
  --output /tmp/loghouse_out
```

This runs normalize → correlate → rules → findings → dispatch.

Check the output:
- `/tmp/loghouse_out/findings.json` — validated finding records
- `/tmp/loghouse_out/findings.md` — human-readable findings report
- `/tmp/loghouse_out/dispatch_queue.json` — agent-routable dispatch items

Expected: at least one finding with evidence and one dispatch item.

---

## Step 3 — Inspect findings

Open `/tmp/loghouse_out/findings.json`.  
Each finding record contains:

| Field | Purpose |
|---|---|
| `finding_id` | Unique UUID; reference in tickets and evidence |
| `category` | `reliability`, `drift`, `aiops`, etc. |
| `severity` | `p0` (critical) → `p3` (low) |
| `confidence` | 0–1 numeric confidence score |
| `evidence` | Linked source records (deploy, log, dependency) |
| `hypothesis` | Machine-generated root cause hypothesis |
| `suggested_fix` | Recommended remediation action |

---

## Step 4 — Validate finding schema

```bash
python -c "
import json
from scripts.common import ROOT, validate_with_schema
findings = json.loads(open('/tmp/loghouse_out/findings.json').read())
schema = ROOT / 'schemas/finding.schema.json'
for f in findings:
    errs = validate_with_schema(f, schema)
    print('OK' if not errs else 'FAIL', f['finding_id'], errs)
"
```

All findings must validate cleanly. A finding without evidence is rejected by the engine.

---

## Step 5 — Review the dispatch queue

Open `/tmp/loghouse_out/dispatch_queue.json`.  
Each dispatch item maps to:

| Field | Purpose |
|---|---|
| `id` | Dispatch item UUID |
| `finding_id` | Links back to the finding |
| `agent_role` | Target CAT role (AUDITOR, BUILDER, REVIEWER, etc.) |
| `owner` | Responsible team |
| `acceptance_criteria` | What "done" looks like for the assigned agent |
| `stop_condition` | When the agent must escalate to ORCHESTRATOR |
| `priority` | `p0`–`p3` inherited from finding severity |

Route the dispatch item to the indicated agent role on the dispatch board
(see `docs/operations/LOGHOUSE_DISPATCH_BOARD.md`).

---

## Step 6 — Run the alignment validator

After producing findings, run the full LOGHOUSE alignment check to confirm
the slice is internally consistent:

```bash
python scripts/cat_validate_loghouse.py --root .
```

This writes `evidence/reports/MP-CAT-A007-4C01_validation_report.json`.

---

## Step 7 — Escalation paths

| Severity | Action |
|---|---|
| P0 | Page ORCHESTRATOR immediately. Do not wait for triage. |
| P1 | Assign to BUILDER or AUDITOR within 30 minutes. |
| P2 | Assign to REVIEWER for root-cause identification within 4 hours. |
| P3 | Log in backlog; SCRIBE documents for learning record. |

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| 0 findings produced | No error spike or forbidden edge in input | Verify raw_signals.json has errors + a deploy event |
| Finding rejected (no evidence) | Raw rule returned empty evidence list | Check the rule function in `scripts/loghouse/rules.py` |
| Schema validation errors | Finding field out of range or wrong type | Inspect the error path returned by `validate_with_schema` |
| Dispatch queue empty | Findings list was empty | Fix finding production first |

---

## References

- Engine: `scripts/cat_loghouse.py`, `scripts/loghouse/`
- Schemas: `schemas/finding.schema.json`, `schemas/dispatch_queue_item.schema.json`
- Dispatch board: `docs/operations/LOGHOUSE_DISPATCH_BOARD.md`
- Architecture diagram: `docs/architecture/loghouse/architecture-flow.mmd`
