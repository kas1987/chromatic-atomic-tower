# Model Routing Skill

## Intent

Make agent behavior deterministic, reviewable, and bounded.

## Inputs

- Mission Pack
- BEAD contract
- CAT manifest
- Current repo state
- Applicable gates
- agents/model_routes.yaml (roles + complexity_routing)

## Steps

1. Confirm mission and BEAD identifiers.
2. Confirm allowed and forbidden paths.
3. Identify assertion being addressed.
4. Classify mission rigor (M1-M4) and execution complexity (C1-C4).
5. Select model class via complexity_routing; apply fallback rules on failure.
6. Capture the routing decision and rationale as evidence.

## Evidence

- routing_decision
- fallback_rationale
- execution log
- validation result
- exception log if applicable
