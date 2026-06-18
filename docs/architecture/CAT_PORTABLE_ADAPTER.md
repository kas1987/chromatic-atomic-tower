# CAT Portable Project Adapter

**Version:** 1.0.0  
**Mission:** MP-CAT-A012-4C01  

The CAT Portable Project Adapter allows any repository to participate in
Chromatic Atomic Tower governance without hosting the full CAT stack. A
project adds a single `.cat/` folder that describes its mission linkage,
current state, and validation configuration. CAT tooling reads this folder
to track cross-repo progress; the host project writes to it after each BEAD
transition.

---

## 1. Folder Structure

```
<project-root>/
└── .cat/
    ├── config.json     # Adapter configuration (static, set once)
    ├── state.json      # Live state snapshot (updated on each transition)
    └── README.md       # Human-readable adapter summary
```

The folder is created by `scripts/cat_adapter_init.py --target <project-root>`.

---

## 2. `config.json` — Adapter Configuration

Validated by `schemas/cat_adapter_config.schema.json`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `adapter_version` | string (`"1.0"`) | yes | Spec version |
| `cat_mission_id` | string | yes | CAT mission this project is associated with |
| `repo_name` | string | yes | Identifier for this repository |
| `cat_repo_url` | string | no | URL or local path to the main CAT repository |
| `sync_mode` | enum `read_only` \| `manual` | yes | How state is updated (default: `read_only`) |
| `validation_rules` | array of strings | no | Schema IDs or filenames to import from CAT |
| `allowed_paths` | array of strings | no | Paths in this repo that CAT validation may reference |

### Minimal example

```json
{
  "adapter_version": "1.0",
  "cat_mission_id": "MP-CAT-A012-4C01",
  "repo_name": "my-project",
  "sync_mode": "read_only"
}
```

---

## 3. `state.json` — Live State Snapshot

Validated by `schemas/cat_adapter_state.schema.json`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `snapshot_timestamp` | string (ISO-8601) | yes | When this snapshot was taken |
| `cat_mission_id` | string | yes | Mission ID (must match config) |
| `mission_status` | string | yes | Current mission status (`approved`, `in_progress`, …) |
| `active_bead_id` | string \| null | yes | Currently active BEAD, or null |
| `last_sync` | string (ISO-8601) \| null | yes | Last time CAT tooling read this file |
| `bead_statuses` | object | no | Map of `bead_id → status` for all known BEADs |

### Minimal example

```json
{
  "snapshot_timestamp": "2026-06-18T14:00:00Z",
  "cat_mission_id": "MP-CAT-A012-4C01",
  "mission_status": "in_progress",
  "active_bead_id": "BEAD-CAT-A012-4C01-02",
  "last_sync": null,
  "bead_statuses": {
    "BEAD-CAT-A012-4C01-01": "completed",
    "BEAD-CAT-A012-4C01-02": "active"
  }
}
```

---

## 4. Sync Protocol

### 4.1 Read-only pull (default `sync_mode: read_only`)

1. The host project's CI or developer runs `scripts/cat_adapter_init.py --target .`
   once to create the initial `.cat/` skeleton.
2. On each BEAD transition the project **writes** `.cat/state.json` with the
   current snapshot (manually or via `cat_adapter_init.py --update-state`).
3. CAT tooling may **read** `.cat/state.json` to include this project's progress
   in cross-repo dashboards or `cat_go.py` evaluations — but **never auto-writes**
   back into the host project.
4. No authentication, secrets, or live connections are required.

### 4.2 Invariants

- CAT never pushes changes to a foreign repo automatically.
- `state.json` is a point-in-time snapshot; it is never the source of truth for
  CAT's own mission registry (that remains `missions/registry/MISSION_REGISTRY.yaml`).
- Sensitive data (tokens, DSNs, credentials) **must not** appear in either file;
  both schemas use `additionalProperties: false` to reject unknown fields.

---

## 5. Validation Rule Export/Import

A project may request CAT schemas by listing them in `config.json → validation_rules`:

```json
"validation_rules": ["bead.schema.json", "intent_envelope.schema.json"]
```

`cat_adapter_init.py --export-schemas --target <dir>` copies the named schemas
into `.cat/schemas/`, allowing the project to run local validation against the
same contracts CAT uses without depending on the live CAT tree.

The host project may then add a CI step:

```bash
python -c "
import json, jsonschema, pathlib
schema = json.load(open('.cat/schemas/bead.schema.json'))
instance = json.load(open('path/to/bead.json'))
jsonschema.validate(instance, schema)
"
```

---

## 6. Generator (`cat_adapter_init.py`)

```
python scripts/cat_adapter_init.py [options]

Options:
  --target DIR          Project root to initialize (default: current directory)
  --mission MISSION_ID  CAT mission ID to link (default: reads active from TOWER_STATE)
  --repo-name NAME      Repository name (default: directory name)
  --sync-mode MODE      read_only | manual (default: read_only)
  --update-state        Refresh .cat/state.json from TOWER_STATE + MISSION_REGISTRY
  --export-schemas      Copy validation_rules schemas into .cat/schemas/
  --dry-run             Print what would be created without writing
```

Exit codes: 0 success · 1 validation error · 2 target-not-found.

---

## 7. Integration with `cat_validate.py`

The adapter schemas are included in `cat_validate.py` VALIDATION_TARGETS so
`python scripts/cat_validate.py --all` covers them automatically:

| Target | Schema |
|--------|--------|
| `adapter config example` | `schemas/cat_adapter_config.schema.json` |
| `adapter state example` | `schemas/cat_adapter_state.schema.json` |

---

## 8. Security Notes

- Neither schema permits credential or DSN fields (`additionalProperties: false`).
- `.cat/` should be committed to the host repo (it contains no secrets).
- `.cat/schemas/` (exported) may be gitignored if schemas are accessed directly
  from the CAT repository.
