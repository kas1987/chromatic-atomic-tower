# Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---:|---:|---:|---|---|
| R-001 | Local model hallucinated success | High | High | Require command evidence and Opus review for final merge | Harness |
| R-002 | Scope drift in worker patch | Medium | High | Allowed files list and diff review | Opus / Cheap Reviewer |
| R-003 | Opus budget overuse | Medium | Medium | Use checkpoint review only, cap Opus calls | User |
| R-004 | Tests absent or weak | High | Medium | Require test plan in tickets | Opus Spec Governor |
| R-005 | Local model edits sensitive code | Medium | High | Escalation triggers for auth/security/data/persistence | Harness |
| R-006 | Queue grows vague or stale | Medium | Medium | Weekly queue prune and status update | Archivist / User |
| R-007 | Conflicting model recommendations | Medium | Medium | Opus final reviewer resolves or escalates to human | Opus |
