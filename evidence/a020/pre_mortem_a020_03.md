# A020-03 Pre-Mortem

Plan: authorize only cross-repository mutation requests with complete CAT
traceability and explicit bounded target paths, while leaving execution to the
approved external worker.

RISK-1: A request mutates CAT governance state through a consumer path.
Trigger: a target path points at missions, beads, state, gates, registry, or
learning records.
Symptom: a supposedly external request can overwrite CAT authority.
Impact: CRITICAL
Mitigation: reject CAT-protected path prefixes in the gate and test a mission
registry target explicitly.

RISK-2: A wildcard allowed path authorizes an unintended concrete target.
Trigger: a target path is not actually covered by the declared pattern set.
Symptom: the gate returns authorized for an out-of-scope path.
Impact: HIGH
Mitigation: match every concrete target against the request's allowed patterns
and reject unmatched paths; test an unrelated target.

RISK-3: A mutation is authorized without an audit trail or rollback reference.
Trigger: the request omits mission/BEAD identity, validation, evidence, or
rollback metadata.
Symptom: an external change cannot be reconstructed or reversed.
Impact: HIGH
Mitigation: require all trace fields in the machine-readable schema and return
them in deterministic decision evidence.

RISK-4: The gate accidentally executes consumer code while validating a request.
Trigger: validation delegates to V2 internals or shells out to the target repo.
Symptom: authorization has side effects before the evidence gate completes.
Impact: HIGH
Mitigation: keep `evaluate_request` pure and test that it leaves the request
unchanged; CLI output is decision JSON only.

Decision: PROCEED

Rationale: all high and critical risks have local, testable mitigations and the
gate has no external execution side effect.
