# Tool Planes

The Chromatic Atomic Harness diagram's **Tool + Context Layer** is enumerated as
a governed registry: [`agents/registry/TOOL_REGISTRY.yaml`](../../agents/registry/TOOL_REGISTRY.yaml)
(validated by `schemas/tool_registry.schema.json`).

| Plane | Status | Implementation |
|-------|--------|----------------|
| git | implemented | `scripts/cat_git_bridge.py`, `.github/workflows/` |
| filesystem | implemented | filesystem-native |
| terminal | implemented | script execution layer |
| web | implemented | harness tool layer |
| llm | implemented | `.agent/model_routes.yaml`, `scripts/cat_kimi.py` |
| database | scaffolded | `schemas/tool_plane_database.schema.json`, `scripts/adapters/database_adapter.py` |
| comms (calendar/email) | scaffolded | `schemas/tool_plane_comms.schema.json`, `scripts/adapters/comms_adapter.py` |
| custom | planned | extensible via the registry |
| third_party | planned | 3rd-party APIs |

## Scaffold contract

The `database` and `comms` planes are **read-only scaffolds**. Each has:

- a **descriptor schema** with `additionalProperties: false` that rejects live
  credentials/DSNs (only a *named* `connection_ref` / `provider_ref` is allowed);
- a **read-only adapter** (`scripts/adapters/`) exposing safe introspection
  (`describe`, `is_read_only`, `supports`, …) while every connecting/mutating
  call raises `ScaffoldError`.

This makes the planes first-class and auditable today, while deferring live
integration — real connections, queries, and sends — to a future,
security-gated mission (tracked as **G-8** in the conformance map). No plane in
this scaffold performs network I/O or handles secrets.
