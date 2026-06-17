# Sprint 002 Operator Guide

## Objective

Sprint 002 builds CAT's evidence gate and closeout engine.

## Standard Workflow

```text
Resolve GO
  -> Implement active BEAD
    -> Generate evidence artifacts
      -> Create evidence bundle
        -> Validate bundle
          -> Dry-run closeout
            -> Review report
              -> Apply closeout only when approved
```

## Commands

```bash
python scripts/cat_resolve_go.py
python scripts/cat_validate.py --all
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml
python scripts/cat_closeout.py --type bead --id BEAD-CAT-002-CLOSEOUT-EXAMPLE --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml --to completed --reason "operator dry run" --dry-run
pytest -q
```

## Good Closeout Behavior

A valid closeout includes:

- evidence bundle;
- required artifact paths;
- passing validation result;
- closeout report;
- JSONL audit event;
- transition event;
- learning note.

## Bad Closeout Behavior

Do not close if:

- evidence is only mentioned in prose;
- artifact paths do not exist;
- validation is failed or blocked;
- the bundle references the wrong BEAD;
- the transition target is invalid;
- learning note is blank.
