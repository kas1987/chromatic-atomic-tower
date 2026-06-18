# CAT ID Naming Convention (Type–Repo–Priority–Complexity)

Adopted with **MP-CAT-A006-4C01**. Applies to **new missions/beads from this point forward only**.
Shipped missions and beads (`MP-CAT-000`..`MP-CAT-005` and their `BEAD-CAT-00N-*`) keep their
legacy three-segment IDs and are **not** renamed.

## Mission ID

```
MP-<repo>-<tier><NNN>-<cx>C<oo>
```

| Segment | Meaning | Values |
|---|---|---|
| `MP` | **Type** — Mission Pack | fixed |
| `<repo>` | **Repo** | `CAT` (Chromatic Atomic Tower) |
| `<tier>` | **Priority tier**, frozen at creation | `S` / `A` / `B` / `C` |
| `<NNN>` | **Global mission number** (3 digits) | `006`, `007`, … |
| `<cx>` | **Complexity** (mission level) | `4`=M4 (highest) … `1`=M1 (lowest) |
| `C` | literal complexity marker | fixed |
| `<oo>` | **Relative execution order** (2 digits) | `01`, `02`, … |

Example: `MP-CAT-A006-4C01` = Mission Pack · CAT · A-tier · mission #006 · complexity M4 · order 01.

## Bead ID

```
BEAD-<repo>-<tier><NNN>-<cx>C<oo>-<bb>
```

Beads inherit the parent mission's stem and add a 2-digit bead sequence `<bb>`.
Example: `BEAD-CAT-A006-4C01-01` … `-08`.

> The `BEAD-` prefix is retained (not `BD-`) so existing schema regexes
> (`^BEAD-[A-Z0-9-]+$`) and tooling continue to match without changes.

## Priority tiers (frozen at creation)

Priority is **baked into the ID at creation and never changes**. Live/current priority is the
mutable `priority` field in the mission file and registry. Reprioritizing a mission updates the
field, **not** the ID — so identifiers stay stable across reprioritization.

| Tier | Maps to legacy `priority` |
|---|---|
| `S` | 1 (critical / active) |
| `A` | 2 (high) |
| `B` | 3 (medium) |
| `C` | 4–5 (low / backlog) |

## Complexity

`<cx>` mirrors the mission `level` field: `M4 → 4`, `M3 → 3`, `M2 → 2`, `M1 → 1`.
`4` is the highest complexity (atomic / M4), `1` the lowest (basic / M1).

## Compatibility notes

- JSON-schema patterns `^MP-[A-Z0-9-]+$` and `^BEAD-[A-Z0-9-]+$` already accept the new IDs — no schema change required.
- The registry adds optional `priority_tier` and `complexity_order` fields for convenience; `priority` remains the source of truth for live priority.
- Scripts that parse the legacy 3-segment `MP-CAT-NNN` form should treat the segment after the repo as an opaque token; do not assume a fixed number of `-`-delimited segments.
