# Runbook: LOGHOUSE Drift Review

**System**: LOGHOUSE Architecture Drift Detection  
**Mission**: MP-CAT-A007-4C01  
**Audience**: CAT Operators, AUDITOR and REVIEWER Agents

---

## Purpose

This runbook describes how to review, classify, and respond to an architecture drift
report produced by the LOGHOUSE drift detector. Drift detection compares observed
dependency edges against the declared rules in `reference/loghouse/architecture_rules.yaml`
and classifies each edge as intentional, accidental, blocked, or unknown.

---

## Prerequisites

- Dependency edges captured in `tests/fixtures/loghouse/dependency_edges.json`
  (or a custom path).
- Architecture rules in `reference/loghouse/architecture_rules.yaml`.
- Python environment with `requirements.txt` installed.

---

## Step 1 — Run the drift detector

The drift detector runs automatically as part of the full pipeline:

```bash
python scripts/cat_loghouse.py \
  --input tests/fixtures/loghouse \
  --output /tmp/loghouse_out
```

To run drift detection in isolation:

```python
from scripts.loghouse.drift import load_architecture_rules, detect_drift
from pathlib import Path
import json

rules = load_architecture_rules(Path("reference/loghouse/architecture_rules.yaml"))
edges = json.loads(Path("tests/fixtures/loghouse/dependency_edges.json").read_text())
report, findings = detect_drift(edges, rules, Path("/tmp/drift_out"))
print(report["summary"])
```

---

## Step 2 — Read the drift report

Open `/tmp/drift_out/drift_report.json`.  
Key fields in the report:

| Field | Purpose |
|---|---|
| `report_id` | Unique UUID for this report |
| `generated_at` | Timestamp of report generation |
| `edges` | List of classified edges |
| `summary` | Count of intentional / accidental / blocked / unknown edges |

Each edge entry carries:
- `edge_id`, `source`, `target`, `edge_type`
- `classification`: one of `intentional`, `accidental`, `blocked`, `unknown`
- `rule_id`: the matching architecture rule (if any)
- `finding_id`: for blocked edges, the finding emitted

---

## Step 3 — Review each classification

### Intentional
- Edge matches an `allowed` rule.
- No action required.
- Confirm the rule is still current (the architecture may have evolved).

### Blocked
- Edge matches a `forbidden` rule.
- A finding has been emitted automatically.
- Check `/tmp/drift_out/findings.json` for the finding details.
- Route via the dispatch queue to the AUDITOR role.
- **P0/P1 blocked edges fail the CI drift gate.**

### Accidental
- No matching rule, and `edge.allowed = false`.
- The edge was not explicitly declared but the team knows it should not exist.
- Create an architecture rule to formalise the prohibition, then rerun detection.

### Unknown
- No matching rule, and `edge.allowed = true` (or unset).
- Either add a new architecture rule to document the intent, or investigate the
  edge source to determine if it is expected.

---

## Step 4 — Update architecture rules (if needed)

Edit `reference/loghouse/architecture_rules.yaml`.  
Each rule must conform to `schemas/architecture_rule.schema.json`:

```yaml
- rule_id: RULE-007
  source: new-service
  target: payments-api
  edge_type: runtime
  decision: allowed          # or: forbidden
  severity: p2               # p0 (critical) | p1 (high) | p2 (medium) | p3 (low)
  rationale: >-
    New service is authorised to call payments-api for checkout flows.
```

After updating rules, rerun drift detection to confirm classifications change correctly.

---

## Step 5 — CI drift gate

The CI drift gate in `.github/workflows/cat-loghouse-ci.yml` runs automatically:

```bash
python scripts/loghouse/drift_gate.py \
  --rules reference/loghouse/architecture_rules.yaml \
  --edges tests/fixtures/loghouse/dependency_edges.json \
  --fail-on p0,p1
```

The gate exits 1 (build failure) if any `forbidden` edge at severity p0 or p1 is present
in the fixture. To run the gate locally:

```bash
make loghouse-gate
```

To run the full LOGHOUSE local check suite:

```bash
make loghouse
```

---

## Step 6 — Escalation paths

| Classification | Who acts | Escalation |
|---|---|---|
| Blocked P0 | AUDITOR immediately | Page ORCHESTRATOR if cannot resolve within 15 min |
| Blocked P1 | AUDITOR within 30 min | Escalate to ORCHESTRATOR if multi-service impact |
| Blocked P2/P3 | REVIEWER for investigation | SCRIBE documents in learning record |
| Accidental | REVIEWER adds/updates rule | BUILDER removes the edge if confirmed forbidden |
| Unknown | REVIEWER investigates | SCRIBE documents for architecture governance |

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| Drift report schema errors | Edge missing required field | Check `dependency_edges.json` format against `schemas/dependency_edge.schema.json` |
| Blocked edge but no finding | Finding has no evidence | Check `rule_forbidden_dependency_edge` in `scripts/loghouse/rules.py` |
| Gate fails on clean fixture | Rule `severity` mismatch | Verify the rule `severity` field in `architecture_rules.yaml` |
| All edges classified unknown | No matching rules | Ensure `source`/`target`/`edge_type` in edges match rule definitions exactly |

---

## References

- Drift detector: `scripts/loghouse/drift.py`
- Drift gate: `scripts/loghouse/drift_gate.py`
- Architecture rules: `reference/loghouse/architecture_rules.yaml`
- Schemas: `schemas/architecture_rule.schema.json`, `schemas/drift_report.schema.json`
- Drift flow diagram: `docs/architecture/loghouse/drift-detection-flow.mmd`
- Dispatch board: `docs/operations/LOGHOUSE_DISPATCH_BOARD.md`
