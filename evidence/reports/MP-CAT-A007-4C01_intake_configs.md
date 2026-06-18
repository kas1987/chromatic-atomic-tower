# MP-CAT-A007-4C01 Intake Configs — BEAD-02

**Date:** 2026-06-18  
**Mission:** MP-CAT-A007-4C01  
**BEAD:** BEAD-CAT-A007-4C01-02  
**Actor:** Builder (GO dispatch)

## Command

```bash
python -c "import yaml,glob; [yaml.safe_load(open(p)) for p in glob.glob('reference/loghouse/*.yaml')]; print('loghouse configs parse OK')"
```

## Output

```
loghouse configs parse OK
```

## Definition of Done

| Criterion | Status |
|-----------|--------|
| `otel-collector.yaml` — receivers, enrichment processors, file/debug exporters | PASS |
| `vector.yaml` — sources, remap transforms, file/console sinks | PASS |
| `reference/loghouse/README.md` — field mapping to `telemetry_envelope` | PASS |
| No secrets; local/placeholder endpoints only | PASS |

## Changes

- `otel-collector.yaml`: per-pipeline `signal_type` (`log` / `metric` / `trace`) via dedicated attribute processors.
- `vector.yaml`: assign `event_id` via `uuid_v4()` when missing from source records.

## Result

**PASS** — intake templates ready for local MVP use.
