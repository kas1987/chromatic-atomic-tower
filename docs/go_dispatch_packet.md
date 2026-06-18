# CAT GO Dispatch Packet

## Overview

`scripts/cat_resolve_go.py` resolves the next work unit for the active mission and emits a **GO dispatch packet** — a structured JSON or Markdown document describing exactly what to do next.

The packet is validated against `schemas/go_dispatch_packet.schema.json`.

## Required Fields

| Field | Type | Description |
|---|---|---|
| `dispatch_status` | `"ready"` \| `"blocked"` | Whether the BEAD is ready to execute |
| `mission_id` | string | Parent mission ID (`MP-CAT-...`) |
| `bead_id` | string | BEAD to execute (`BEAD-CAT-...`) |
| `bead_title` | string | Human-readable BEAD title |
| `allowed_paths` | string[] | Files the agent may write |
| `forbidden_paths` | string[] | Files the agent must not touch |
| `validation` | object[] | Validation commands with evidence paths |
| `stop_conditions` | string[] | Conditions that halt execution |

## Optional Fields

| Field | Type | Description |
|---|---|---|
| `reason` | string | Why the BEAD was selected or blocked |
| `mission_title` | string | Human-readable mission title |
| `mission_level` | string | M1–M4 complexity level |
| `agent_role` | string | Required agent role |
| `autonomy_level` | string | L1–L4 autonomy level |
| `confidence` | number | Current BEAD confidence score |
| `confidence_minimum` | number | Minimum required to dispatch |
| `confidence_band` | string | `very_high`/`high`/`medium`/`low`/`blocked` |
| `risk_level` | string | `low`/`medium`/`high`/`critical` |
| `reversibility` | string | `high`/`medium`/`low` |
| `tool_budget` | object | Per-tool budget limits |
| `definition_of_done` | string[] | DoD checklist |
| `required_output` | string[] | Required output artifacts |
| `bead_path` | string | Path to BEAD YAML contract |
| `mission_path` | string | Path to mission YAML |

## Dispatch Blocking

The resolver blocks dispatch when:
- `confidence.current < confidence.minimum` → status: `blocked`
- Tower–registry mission/BEAD alignment drift detected (skipped in `--check-schema` mode)
- LOGHOUSE self-monitor reports critical findings

## Commands

### JSON output

```bash
python scripts/cat_resolve_go.py --json
# or equivalently:
python scripts/cat_resolve_go.py --format json
```

### Markdown output (default)

```bash
python scripts/cat_resolve_go.py
# or:
python scripts/cat_resolve_go.py --format markdown
```

### Validate dispatch packet against schema

```bash
python scripts/cat_resolve_go.py --format json --check-schema
```

Exits 0 and prints `SCHEMA PASS` if the packet validates. Exits 1 with `SCHEMA FAIL` and error details if not.

`--check-schema` automatically skips the alignment and LOGHOUSE gates (it is a schema probe, not a real dispatch).

### Kickoff with queued BEAD (operator only)

```bash
python scripts/cat_resolve_go.py --allow-queued
```

## Confidence Bands

| Score | Band |
|---|---|
| ≥ 90 | `very_high` |
| 75–89 | `high` |
| 60–74 | `medium` |
| 40–59 | `low` |
| < 40 | `blocked` |

## Schema

The full schema is at `schemas/go_dispatch_packet.schema.json` (JSON Schema 2020-12).
