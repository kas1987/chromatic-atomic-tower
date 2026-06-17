# Confidence Gate

## Purpose

Prevent agents from mutating state before the objective, scope, evidence, risk, reversibility, tools, and validation are clear.

## Score formula

```text
confidence =
  objective_clarity * 0.20 +
  scope_clarity * 0.20 +
  evidence_quality * 0.20 +
  reversibility * 0.10 +
  tool_fit * 0.10 +
  risk_awareness * 0.10 +
  testability * 0.10
```

## Bands

| Score | Band | Permission |
|---:|---|---|
| 90-100 | Very High | Execute scoped work |
| 75-89 | High | Execute with normal logging |
| 60-74 | Medium | Reversible low-risk work only |
| 40-59 | Low | Plan only |
| 0-39 | Blocked | Halt |

## Override rule

Human gate requirements override confidence scores.
