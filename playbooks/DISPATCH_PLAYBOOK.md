# Dispatch Playbook

## Purpose

Standardize agent dispatch from a BEAD.

## Dispatch packet

Every dispatch includes:

- Mission ID
- BEAD ID
- role
- autonomy level
- confidence
- risk
- allowed paths
- forbidden paths
- tool budget
- stop conditions
- definition of done
- validation
- required output

## Dispatch command

```bash
python scripts/cat_resolve_go.py
```

## Stop before dispatch when

- confidence is below minimum
- active BEAD is missing
- human gate is required
- forbidden path is needed
- validation is undefined
