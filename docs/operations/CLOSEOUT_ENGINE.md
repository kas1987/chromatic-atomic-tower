# Closeout Engine

## Executive Summary

The Closeout Engine connects evidence validation to CAT lifecycle transitions.

It validates an evidence bundle, writes a closeout report, logs a closeout event, and delegates the final state movement to the Sprint 001 transition engine.

## Dry-Run Closeout

```bash
python scripts/cat_closeout.py \
  --type bead \
  --id BEAD-CAT-002-001 \
  --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml \
  --to completed \
  --reason "dry-run closeout validation" \
  --dry-run
```

## Applied Closeout

Use this only after review:

```bash
python scripts/cat_closeout.py \
  --type bead \
  --id BEAD-CAT-002-001 \
  --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml \
  --to completed \
  --reason "evidence validated and review complete" \
  --move
```

## Outputs

The closeout engine writes:

- closeout report in `evidence/reports/`
- closeout event in `evidence/logs/closeouts.jsonl`
- transition event in `evidence/logs/transitions.jsonl`

## Stop Conditions

Stop if:

- required artifact is missing;
- required validation failed;
- bundle ID does not match target ID;
- transition engine rejects the target state;
- mission closure lacks a learning note.
