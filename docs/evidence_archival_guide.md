# CAT Evidence Archival Guide

## Purpose

CAT retains evidence in git while moving eligible records older than 90 days
under `evidence/archive/YYYY/QN/`. Scorecards, learnings, evidence bundles,
and gate results are exempt and remain in place.

## Inspect and preview

Run the commands from the repository root. Global options precede the
subcommand:

```text
python scripts/cat_archive_evidence.py status
python scripts/cat_archive_evidence.py --older-than 90 dry-run
```

`dry-run` does not move files. It reports eligible records and emits skipped
records for exempt paths.

## Execute

```text
python scripts/cat_archive_evidence.py --older-than 90 --batch-id BATCH_ID run
```

The command creates `evidence/archive/YYYY/QN/` as needed and writes an audit
JSONL record under `evidence/logs/archival_*.jsonl`. A no-candidate run is a
valid no-op and still produces an audit log.

## Recovery

Before committing an archival run, inspect the JSONL records and confirm every
source has the expected destination. To recover a moved file, move it back from
the recorded `destination_path` to `source_path`, then run:

```text
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
```

The archive is tracked by git; use `git log --all -- evidence/archive/` to
locate the history of an archived artifact.
