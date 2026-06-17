# LOGHOUSE Foundation (Phase 1)

## Purpose

Define the first implementation slice for LOGHOUSE in CAT:

- canonical telemetry and findings contracts
- schema-level validation for fast feedback
- deterministic foundation before adding ML/anomaly layers

## Initial Contracts

- `schemas/telemetry_envelope.schema.json`
- `schemas/finding.schema.json`
- `schemas/dependency_edge.schema.json`
- `schemas/deploy_event.schema.json`

## Required Telemetry Attributes

All ingested telemetry should include:

- `service`
- `env`
- `signal_type`
- `ts`
- `commit_sha`
- `deploy_id`

If unavailable at source, these should be enriched in ingestion pipelines.

## Findings Quality Bar

Every finding must include:

- owner
- hypothesis
- suggested_fix
- at least one evidence item
- confidence score in `[0,1]`

## Validation

```bash
python -m pytest -q tests/test_loghouse_schemas.py
python scripts/cat_validate.py --all
```

## Next Steps (Phase 2)

- findings-engine rule skeleton
- first deterministic rules (error spike after deploy, forbidden edge, exception explosion)
- replay fixtures and output templates
