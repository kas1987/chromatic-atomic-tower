# CAT ID Naming Convention and Taxonomy

The machine-readable source of truth is
[`gates/CAT_ID_TAXONOMY.yaml`](../../gates/CAT_ID_TAXONOMY.yaml), version 2.0.0.
This document is its human-readable projection. New records use the current
form; historical identifiers are preserved and are never renamed.

## Mission ID

```text
MP-<repo>-<class><NNN>-<cx>C<oo>
```

| Segment | Meaning |
|---|---|
| `MP` | Mission Packet type |
| `<repo>` | Repository/project namespace (`CAT`) |
| `<class>` | Descriptive mission class at creation (`S`, `A`, `B`, or `C`) |
| `<NNN>` | Immutable global mission sequence |
| `<cx>` | Legacy compact complexity display (`4` = M4 through `1` = M1) |
| `C` | Compact complexity marker |
| `<oo>` | Execution order or profile code |

Example: `MP-CAT-A006-4C01` means Mission Packet, CAT, class A, mission 006,
compact M4 display, order/profile 01. `A006` is not a PR number or branch name.
PR numbers, branches, and exact head SHAs are external relations recorded in
mission, BEAD, and evidence fields.

## Bead ID

```text
BEAD-<repo>-<class><NNN>-<cx>C<oo>-<bb>
```

BEADs inherit the parent mission stem and append an immutable two-digit
sequence. Legacy `MP-CAT-NNN` and `BEAD-CAT-NNN-*` forms remain valid.

## Urgency, impact, effort, and control

These are separate dimensions. `priority` is the only urgency axis and remains
the current numeric storage field; lower numbers are more urgent. For quick
reads, use the compatibility display `1→P0`, `2→P1`, `3→P2`, `4→P3`, `5→P4`.
This display map does not rewrite stored records.

| Field | Answers | May influence |
|---|---|---|
| `priority` | How urgently should this be handled? | Queue order and escalation |
| `severity` | How bad is failure or a defect? | Assurance depth and attention |
| `complexity` / `level` | How difficult or uncertain is the work? | Planning and model capability hint |
| `risk_level` | What is the probability/blast radius? | Safeguards and approval |
| `reversibility` | How easy is rollback? | Approval and rollback requirements |
| `hitl_mode` | What human control is required? | Dispatch and promotion gates |
| `mission_class` | What class was assigned at creation? | None; never routing |

Agents must not infer urgency, severity, HITL, authority, or promotion rights
from `S/A/B/C`, `4C01`, mission number, or a branch/PR label.

## Compatibility

- Existing IDs and numeric priority values are preserved.
- `priority_tier` and `complexity_order` are legacy/derived fields, not
  canonical routing truth.
- Generic schema patterns continue to accept both ID families.
- Consumer, schema, and registry canonicalization is follow-on work under
  A023 BEADs 02–05.
