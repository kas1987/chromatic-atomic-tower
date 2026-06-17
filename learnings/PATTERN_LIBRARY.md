# Pattern Library

## Pattern: Donor not foundation

When replacing a legacy Harness, use it as source material but start from a clean architecture.

## Pattern: BEAD-first execution

Agents perform better when the unit of work is atomic, bounded, and validated.

## Pattern: Evidence before closeout

Require proof artifacts before work is declared complete.

## Anti-pattern: Documentation as permission

Long prose can mislead agents. Operational permission belongs in validated contracts.

## Pattern: Schema-gate every model-authored contract

Output from any LLM (local or cloud) that becomes a CAT contract must validate against its
JSON schema BEFORE it is staged for the human gate. The model is a drafter inside mission
authority, not an authority itself. Demonstrated MP-CAT-001: the cloud model's first draft
failed schema validation with 8 violations (invented enums, wrong types/shapes); only the
validator's verdict — not the model's confidence — gated promotion.

## Pattern: Validator-feedback repair loop

When a model-authored contract fails schema validation, feed the exact validator error list
back to the same model for a bounded correction round, then re-validate. One round fixed all
8 MP-CAT-001 violations. Cheaper and more faithful to provenance than hand-editing the output.

## Anti-pattern: Trusting model self-report over the gate

Models emit plausible-but-invalid enum values and types (e.g. `autonomy_level: human_gated`,
`confidence_minimum: 0.85`). Never promote on the model's say-so; promote on the validator's.
