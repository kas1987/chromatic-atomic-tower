# A020-04 Pre-Mortem

Plan: enforce a machine-readable, one-direction canonical-to-derived ownership
DAG and reject any graph with duplicate or conflicting writers.

RISK-1: A generated artifact becomes a second canonical writer.
Trigger: the same path appears as both a canonical path and a derived artifact.
Symptom: future transitions cannot identify the authoritative source.
Impact: CRITICAL
Mitigation: index canonical and derived paths and reject overlap before any
ownership result is accepted.

RISK-2: Conflicting writers are silently resolved by ordering.
Trigger: duplicate fact IDs or canonical paths are encountered.
Symptom: whichever record appears last controls the result.
Impact: HIGH
Mitigation: accumulate explicit conflict errors and return `rejected` without
selecting a writer; test duplicate IDs and cross-writer paths.

RISK-3: A derived artifact points to an unknown source fact.
Trigger: source_fact is misspelled or references a removed canonical fact.
Symptom: the graph looks structurally valid but cannot be traced.
Impact: HIGH
Mitigation: require source references to resolve to a declared fact and test
unknown-source rejection.

Decision: PROCEED

Rationale: the guard is read-only, deterministic, and every identified risk has
a schema or semantic validation proof within the BEAD scope.
