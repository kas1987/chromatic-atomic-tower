# LLM Model Routing Policy

CAT should route work from the independent fields in
`gates/CAT_ID_TAXONOMY.yaml`. Complexity is a capability hint, while priority,
risk, severity, reversibility, and HITL determine urgency and control. The
machine-readable route policy remains in `agents/model_routes.yaml`.

## Two-axis model

| Axis | Meaning |
|---|---|
| priority | Queue urgency and escalation order |
| severity | Impact and assurance depth |
| complexity | Effort and uncertainty; model capability hint |
| risk_level | Safeguards and approval depth |
| reversibility | Rollback and approval requirements |
| hitl_mode | Human control boundary |

## Routing principle

Use the lowest sufficient model and agent path, then escalate when evidence shows the route is insufficient.

## Routing matrix

| Contract signal | Default route | Escalation |
|---|---|---|
| M1/M2, low risk, review-required or lower HITL | local fast/coding alias | Stronger reviewer when the proof gate fails |
| M3, or cross-component work | strong reasoning alias | Human review when ambiguity or repeated validation failure remains |
| M4, high/critical risk, low reversibility, or human-only HITL | strongest approved reviewer plus human gate | Security/governance review; never silent downgrade |

## Fallback triggers

- repeated validation failure
- ambiguity in mission scope
- security-sensitive file path
- cross-system change
- high cost drift
- hallucinated dependency or nonexistent file
- confidence score below threshold

## Non-negotiables

- No model can bypass CAT gates.
- No model can modify forbidden paths.
- No model can close a mission without evidence and the required HITL gate.
- Narrative confidence is not evidence.
- Mission class, compact complexity text, mission number, PR number, and branch
  names are not routing authority.
