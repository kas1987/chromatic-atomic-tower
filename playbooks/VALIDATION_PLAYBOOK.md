# Validation Playbook

## Purpose

Define what proves work is done.

## Validation levels

| Risk | Minimum validation |
|---|---|
| low | self-review and repo check |
| medium | schema validation or targeted test |
| high | test, review, and evidence report |
| critical | human gate plus audit evidence |

## Required evidence

- command run
- result
- output location
- failures if any
- reviewer decision if applicable

## Default Sprint 000 commands

```bash
python scripts/cat_check_repo.py
python scripts/cat_validate.py --all
python scripts/cat_resolve_go.py
```
