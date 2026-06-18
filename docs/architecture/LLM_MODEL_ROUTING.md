# LLM Model Routing Policy

CAT should route missions by both mission rigor and execution complexity.
The machine-readable policy lives in `agents/model_routes.yaml` (`complexity_routing`).

## Two-axis model

| Axis | Meaning |
|---|---|
| M1-M4 | Governance and mission rigor |
| C1-C4 | Technical execution complexity |

## Routing principle

Use the lowest sufficient model and agent path, then escalate when evidence shows the route is insufficient.

## Routing matrix

| Mission | Complexity | Default route (model class) | Concrete model | Escalation |
|---|---|---|---|---|
| M1 | C1 | local_fast | minimax-m3:cloud | Reviewer only if validation fails |
| M2 | C2 | local_coding | kimi-k2.7-code:cloud | Strong coding model if tests fail twice |
| M3 | C3 | strong_coding_reasoning | claude-sonnet-4-6 | Frontier model if architecture or risk ambiguity remains |
| M4 | C4 | frontier_reasoning + human gate | claude-opus-4-8 | Governance council / security / auditor |

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
- No model can close a mission without evidence.
- Narrative confidence is not evidence.
