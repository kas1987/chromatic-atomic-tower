# A020-02 Pre-Mortem

Plan: define a versioned portable CAT adapter contract whose schemas make the
consumer read/write boundary explicit without granting a consumer CAT write
authority.

RISK-1: The adapter contract permits a consumer to write CAT governance state.
Trigger: a configuration or state example includes non-empty CAT write paths.
Symptom: a schema-valid adapter can claim authority over `missions/`, `beads/`,
or CAT-derived state.
Impact: HIGH
Mitigation: require `cat_authority.write_paths` and the state equivalent to be
empty arrays using a JSON Schema `maxItems: 0` constraint; test rejection of a
non-empty value.

RISK-2: Consumers silently use an incompatible adapter contract version.
Trigger: a future or malformed version is accepted by the portable schemas.
Symptom: a consumer validates locally while interpreting fields with different
authority semantics.
Impact: HIGH
Mitigation: require the exact `1.0.0` contract version in both schemas and
document major-version rejection plus explicit negotiation for future versions.

RISK-3: Runtime evidence is present but cannot prove which bounded execution it
belongs to.
Trigger: state omits the mission, BEAD, validation command, or evidence path.
Symptom: CAT receives an untraceable success/failure snapshot.
Impact: HIGH
Mitigation: require mission ID, active BEAD ID, execution status, evidence
path, validation command, and validation result in the state schema and cover
missing/invalid evidence in tests.

RISK-4: Path fields create a traversal or external-path escape surface.
Trigger: an adapter declares absolute paths or `..` segments.
Symptom: validation references files outside the consumer repository boundary.
Impact: MEDIUM
Mitigation: constrain portable paths to non-absolute, repository-relative
strings without traversal segments and test representative invalid paths.

Decision: PROCEED

Rationale: every identified high or medium risk has a machine-checkable,
reversible mitigation within the A020-02 allowed paths.
