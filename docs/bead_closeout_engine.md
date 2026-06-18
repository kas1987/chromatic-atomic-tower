# CAT BEAD Closeout Engine

## Overview

`scripts/cat_closeout.py` enforces evidence-gated closeout for missions and BEADs.
It validates an evidence bundle, generates a closeout report, and then calls
`cat_transition.py` to mutate state — all in one atomic operation.

No BEAD or mission may be closed without passing the evidence gate.

## How It Works

```text
cat_closeout.py
  ├── validate_bundle(bundle_path)        # checks artifacts exist, validation_result OK
  ├── ID-match check                      # bundle IDs must match target IDs
  ├── write_closeout_report()             # markdown report in evidence/reports/
  ├── run_closeout() → apply_transition() # only if validation passed
  └── append_closeout_event()             # audit log in evidence/logs/closeouts.jsonl
```

## Evidence Bundle

A bundle is a YAML file (typically in `evidence/bundles/generated/`) describing:
- `target_type`: `mission` or `bead`
- `mission_id` / `bead_id`
- `validation_result`: must be `passed`
- `required_artifacts`: list of `{path, kind, required: true}` entries
- `summary`, `learning_note`

All `required: true` artifacts must exist on disk. A missing artifact blocks closeout.

See: `schemas/evidence_bundle.schema.json`, `evidence/bundles/examples/`.

## Evidence Manifest

`evidence/manifest.yaml` is a queryable index of all artifacts produced during
BEAD execution, keyed by `evidence_id`. Format follows `schemas/evidence_manifest.schema.json`.

Fields per entry: `evidence_id`, `mission_id`, `bead_id`, `artifact_path`,
`artifact_type`, `generated_at`, `validator`, `sha256`.

`sha256` is updated by `cat_evidence_index.py --rebuild` (BEAD-CAT-A014-4C01-03).

## Usage

### Dry-run (validate without closing)

```bash
python scripts/cat_closeout.py \
  --type bead \
  --id BEAD-CAT-A014-4C01-01 \
  --bundle evidence/bundles/generated/EB-A014-01.yaml \
  --to completed \
  --reason "BEAD-01 implementation complete" \
  --actor "Auditor" \
  --dry-run
```

### Execute closeout

```bash
python scripts/cat_closeout.py \
  --type bead \
  --id BEAD-CAT-A014-4C01-01 \
  --bundle evidence/bundles/generated/EB-A014-01.yaml \
  --to completed \
  --reason "BEAD-01 implementation complete" \
  --actor "Auditor"
```

### JSON output

Add `--json` to get machine-readable output.

## Audit Log

All closeout events are appended to `evidence/logs/closeouts.jsonl`.

Fields: `timestamp`, `target_type`, `target_id`, `to_status`, `bundle`, `allowed`,
`dry_run`, `reason`, `actor`, `message`, `errors`, `report`.

## Gates That Block Closeout

| Condition | Error |
|---|---|
| Missing required artifact on disk | `missing required artifact: <path>` |
| `validation_result != passed` | Bundle shows failed validation |
| Bundle ID ≠ requested target ID | `bead_id does not match` |
| Bundle type ≠ requested type | `target_type does not match` |
