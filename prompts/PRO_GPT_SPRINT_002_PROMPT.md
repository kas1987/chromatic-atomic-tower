# Pro GPT Prompt — CAT Sprint 002

You are operating inside Chromatic Atomic Tower Sprint 002.

## Mission

Implement and operate the Evidence Gate + Closeout Engine.

## Core Rule

```text
No Evidence Bundle = No BEAD Completion
No Closeout Report = No Mission Closure
No Learning Note = No Final Done
```

## Required Behavior

1. Resolve current work with `python scripts/cat_resolve_go.py`.
2. Stay inside allowed paths from the active BEAD.
3. Validate contracts with `python scripts/cat_validate.py --all`.
4. Validate evidence bundles before closeout.
5. Use dry-run before applied closeout.
6. Record evidence and learning.
7. Do not mutate forbidden paths.

## Sprint 002 Commands

```bash
python scripts/cat_validate.py --all
python scripts/cat_evidence.py validate --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml
python scripts/cat_closeout.py --type bead --id BEAD-CAT-002-CLOSEOUT-EXAMPLE --bundle evidence/bundles/examples/EB-CAT-002-EXAMPLE.yaml --to completed --reason "dry-run closeout validation" --dry-run
pytest -q
```

## Stop Conditions

Stop if evidence is missing, validation fails, target IDs mismatch, or completion would require a forbidden path.
