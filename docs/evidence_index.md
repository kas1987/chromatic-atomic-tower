# CAT Evidence Index

## Overview

`scripts/cat_evidence_index.py` maintains `evidence/manifest.yaml` — a queryable
index of all evidence artifacts produced during BEAD and mission execution.

Each entry records: who produced the artifact, which BEAD it belongs to, when it
was created, and its SHA-256 hash for integrity verification.

## Schema

`evidence/manifest.yaml` follows `schemas/evidence_manifest.schema.json`:

```yaml
schema_version: 0.1.0
generated_at: '2026-06-18T16:00:00+00:00'
evidence:
  - evidence_id: EVD-A014-4C01-001
    mission_id: MP-CAT-A014-4C01
    bead_id: BEAD-CAT-A014-4C01-01
    artifact_path: evidence/reports/state-transition-test-output.txt
    artifact_type: test_output
    generated_at: '2026-06-18T16:22:00+00:00'
    validator: pytest
    sha256: <64-char hex>
```

### artifact_type values

| Type | Description |
|---|---|
| `test_output` | Pytest or unit test run output |
| `closeout_report` | Markdown closeout report |
| `validation_log` | cat_validate.py or cat_check_repo.py output |
| `diff` | Patch or diff file |
| `screenshot` | PNG/JPG visual evidence |
| `bundle` | Evidence bundle YAML |
| `other` | Anything else |

## Commands

### Validate the existing manifest

```bash
python scripts/cat_evidence_index.py --check
```

Exits nonzero if:
- `schema_version` is missing
- Any entry is missing a required field
- Any `artifact_path` does not exist on disk
- Any `evidence_id` is duplicated
- Any `sha256` is not a valid 64-char hex string

### Rebuild manifest from evidence/ folder

```bash
python scripts/cat_evidence_index.py --rebuild
```

Scans all files under `evidence/` (excluding `snapshots/` and `bundles/`) and
creates new entries. Overwrites existing manifest. Sets `mission_id` and `bead_id`
to `UNKNOWN` — edit manually or via `--add` after rebuild.

### Update sha256 hashes

```bash
python scripts/cat_evidence_index.py --update-hashes
```

Replaces any `placeholder_to_be_updated_by_cat_evidence_index` values with the
real SHA-256 of the artifact on disk.

## Workflow

1. After running validation commands, write evidence artifacts to `evidence/reports/`.
2. Add entries to `evidence/manifest.yaml` with the correct mission/BEAD IDs.
3. Run `python scripts/cat_evidence_index.py --update-hashes` to hash the artifacts.
4. Run `python scripts/cat_evidence_index.py --check` to confirm validity.
5. Reference the manifest in the evidence bundle for closeout.

## Integration

- `cat_closeout.py` — uses evidence bundles (not the manifest directly), but
  the manifest provides a queryable audit trail for all artifacts
- `cat_evidence.py` — generates individual evidence bundles
- `cat_evidence_index.py` — maintains the cross-BEAD index
