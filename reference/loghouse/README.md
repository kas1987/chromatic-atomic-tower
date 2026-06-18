# LOGHOUSE Intake Configuration Reference

This directory contains local-first intake configuration templates for LOGHOUSE.
These are **reference templates** — they require no live backend, no secrets, and no external services for the MVP.

## Files

| File | Purpose |
|---|---|
| `otel-collector.yaml` | OpenTelemetry Collector pipeline (logs, metrics, traces) |
| `vector.yaml` | Vector/Fluent Bit log pipeline |
| `dependency-cruiser.cjs` | Dependency-cruiser rule template for static graph extraction |
| `architecture_rules.yaml` | Architecture rule set (validated against architecture_rule.schema.json) |

## Raw Signal → Telemetry Envelope Field Mapping

LOGHOUSE requires six attributes on every ingested signal. The intake configs inject them via environment variables if not present at the signal source.

| telemetry_envelope field | OTel Collector source | Vector source |
|---|---|---|
| `service` | `service.name` resource attribute | `.service` or `LOGHOUSE_SERVICE` env |
| `env` | `deployment.environment` resource attribute | `.env` or `LOGHOUSE_ENV` env |
| `signal_type` | Pipeline kind (logs/metrics/traces) | `.signal_type` or literal `"log"` |
| `ts` | Event timestamp | `.ts`, `.timestamp`, or `.time` |
| `commit_sha` | `loghouse.commit_sha` attribute / `$COMMIT_SHA` | `.commit_sha` or `$COMMIT_SHA` env |
| `deploy_id` | `loghouse.deploy_id` attribute / `$DEPLOY_ID` | `.deploy_id` or `$DEPLOY_ID` env |

Additionally mapped:

| telemetry_envelope field | OTel source | Vector source |
|---|---|---|
| `severity` | Severity text / number | `.severity`, `.level` |
| `message` | Log body | `.message`, `.msg` |
| `trace_id` | Trace context | `.trace_id` |
| `span_id` | Span context | `.span_id` |
| `attrs` | Extra attributes object | Remaining fields in `.attrs` |

## Local Endpoints

OTel Collector listens on:
- gRPC: `localhost:4317`
- HTTP: `localhost:4318`
- Health: `localhost:13133`

Outputs write to `/tmp/loghouse/` — no external connectivity required.

## Usage (MVP / Dev)

```bash
# Set enrichment variables
export COMMIT_SHA=$(git rev-parse --short HEAD)
export DEPLOY_ID="deploy-local-$(date +%Y%m%d)"
export LOGHOUSE_SERVICE="my-service"
export LOGHOUSE_ENV="dev"

# Validate configs parse correctly
python -c "import yaml,glob; [yaml.safe_load(open(p)) for p in glob.glob('reference/loghouse/*.yaml')]; print('loghouse configs parse OK')"
```

## No Secrets Policy

These configs use only:
- Environment variables for runtime values
- Local file paths (`/tmp/loghouse/`)
- Local network endpoints (`localhost`)

**Do not add API keys, tokens, or credentials to these files.**
