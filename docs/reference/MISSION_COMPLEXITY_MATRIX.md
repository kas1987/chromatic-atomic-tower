# Mission Complexity Matrix

The machine-readable source of truth is
[`gates/CAT_ID_TAXONOMY.yaml`](../../gates/CAT_ID_TAXONOMY.yaml). Complexity is
an estimate of effort and uncertainty; it is not a proxy for urgency, impact,
risk, reversibility, or human authority.

| Complexity | Meaning | Planning/model hint |
|---|---|---|
| M1 | One bounded change with a clear proof gate | Fast local path is usually sufficient |
| M2 | Several steps or limited dependencies | Coding path with targeted review |
| M3 | Multiple components, systems, or substantial validation | Strong reasoning and broader evidence |
| M4 | Cross-plane or high-uncertainty work requiring deep coordination | Highest-capability route plus explicit gates |

## Independent control axes

Use the other contract fields for the questions complexity cannot answer:

- `priority` / P0–P4: urgency and queue order; lower stored numeric values are more urgent.
- `severity`: impact if the change fails; drives assurance depth.
- `risk_level`: probability and blast radius; drives safeguards and approval.
- `reversibility`: ease of rollback; drives rollback planning.
- `hitl_mode`: the human control boundary; drives dispatch and promotion.

Agents and routers must evaluate these fields explicitly. They must not infer
that M4 is critical, irreversible, or human-only without the corresponding
severity, risk, reversibility, and HITL values.
