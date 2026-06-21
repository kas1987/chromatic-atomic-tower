# Archive Schema Reference

**File:** `schemas/archive.schema.json`  
**Version:** 1.0.0  
**Last Updated:** 2026-06-21

---

## Purpose

The Archive Schema defines the structure and validation rules for evidence archival records. Every archival operation (whether successful, skipped, or failed) produces one archive record conforming to this schema.

---

## Required Fields

Every archive record MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | UTC timestamp of archival operation |
| `source_path` | string | Original path in `evidence/` before archival |
| `destination_path` | string\|null | Destination in `evidence/archive/YYYY/QN/` after archival (null if skipped) |
| `file_size_bytes` | integer | Size of file in bytes (≥0) |
| `event` | enum | Outcome: `archived`, `skipped`, `failed` |
| `eligibility` | enum | Classification: `eligible`, `exempted`, `unknown` |

---

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `reason` | string | Explanation if skipped or failed (e.g., "scorecard records retained indefinitely") |
| `git_commit_sha` | string\|null | Git commit SHA if changes committed immediately |
| `age_days` | number | Age of evidence in days at time of archival |
| `archival_batch_id` | string | Batch ID for grouping related operations in a single run |

---

## Eligibility Enum

### `eligible`
Evidence older than threshold (default 90 days) that should be archived to `evidence/archive/YYYY/QN/`.

**Examples:**
- CI reports (`evidence/ci/*.json`)
- BEAD execution logs (`evidence/logs/*.jsonl`)
- Test result diffs (`evidence/diffs/*.patch`)
- Manual test screenshots (`evidence/manual/*.json`)

### `exempted`
Evidence that is NOT archived regardless of age. Kept in active `evidence/` indefinitely.

**Examples:**
- Agent scorecard records (`agents/scorecards/*.yaml`) — high-signal, small volume
- Learnings (`learnings/*.md`) — governance history, permanent value
- Evidence gate results (`evidence/gate_results/*.json`) — audit trail, permanent

### `unknown`
Uncategorized evidence. Should be reviewed and classified before archival.

---

## Event Enum

### `archived`
File successfully moved to `evidence/archive/YYYY/QN/`. Destination_path is populated.

### `skipped`
File NOT moved (eligible=exempted or other reason). Destination_path is null, reason field populated.

### `failed`
Archival operation failed (e.g., file permissions, git error). Destination_path is null, reason field populated.

---

## Archive Directory Structure

Archive records are organized by year and quarter:

```
evidence/archive/
  2026/
    Q2/  (April–June)
      cat_ci_report_MP_CAT_A011_4C01.json
      BEAD_CAT_A011_4C01_01_execution.jsonl
      ...
    Q3/  (July–September)
      ...
  2027/
    Q1/  (January–March)
      ...
```

**Quarter mapping:**
- Q1: January (01) – March (03)
- Q2: April (04) – June (06)
- Q3: July (07) – September (09)
- Q4: October (10) – December (12)

---

## Example Records

### Example 1: Successful Archival

```json
{
  "timestamp": "2026-06-21T12:00:00Z",
  "source_path": "evidence/ci/cat_ci_report_MP_CAT_A011_4C01.json",
  "destination_path": "evidence/archive/2026/Q2/cat_ci_report_MP_CAT_A011_4C01.json",
  "file_size_bytes": 45000,
  "event": "archived",
  "eligibility": "eligible",
  "age_days": 94,
  "git_commit_sha": "abc123def456",
  "archival_batch_id": "batch_2026_06_21_001"
}
```

### Example 2: Exempted (Scorecard)

```json
{
  "timestamp": "2026-06-21T12:00:00Z",
  "source_path": "agents/scorecards/BEAD-CAT-A011-4C01-01_Builder_bead_completed.yaml",
  "destination_path": null,
  "file_size_bytes": 256,
  "event": "skipped",
  "eligibility": "exempted",
  "reason": "scorecard records retained indefinitely per Evidence Archival Policy",
  "age_days": 100,
  "archival_batch_id": "batch_2026_06_21_001"
}
```

### Example 3: Exempted (Learnings)

```json
{
  "timestamp": "2026-06-21T12:00:00Z",
  "source_path": "evidence/logs/transitions.jsonl",
  "destination_path": null,
  "file_size_bytes": 12000,
  "event": "skipped",
  "eligibility": "exempted",
  "reason": "learnings and logs retained indefinitely per Evidence Archival Policy",
  "age_days": 150,
  "archival_batch_id": "batch_2026_06_21_001"
}
```

---

## Validation Rules

All archive records are validated via jsonschema Draft 2020-12:

```bash
python scripts/cat_validate.py --file schemas/archive.schema.json
```

Every record produced by `cat_archive_evidence.py` MUST conform to this schema.

---

## Integration Points

### 1. cat_archive_evidence.py
Produces archive records after each successful/skipped/failed archival operation.

### 2. cat_check_repo.py
Validates archive records conform to this schema. Reports any invalid records.

### 3. evidence/logs/archival_*.jsonl
All archive records are logged here for audit trail.

### 4. evidence/archival/BEAD-CAT-A015-4C01-01_schema.json
Evidence artifact produced by BEAD-CAT-A015-4C01-01 (this BEAD).

---

## Future Extensions

Future versions may add:

- Retention policies by source type (e.g., CI reports: 90 days, other: 180 days)
- Archive encryption/compression metadata
- Cross-repo archival coordination
- Archive age stratification (archive → compress → delete after N years)
