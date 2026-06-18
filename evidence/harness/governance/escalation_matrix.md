# Escalation Matrix

| Condition | Escalate To | Reason |
|---|---|---|
| Worker fails same ticket twice | Opus | Spec may be wrong or task is harder than expected |
| Patch touches security/auth/secrets | Opus + Human | High-risk domain |
| Patch changes dependencies | Opus + Human | Supply chain / compatibility risk |
| Patch modifies more than five files | Opus | Scope drift risk |
| Tests fail but worker claims success | Opus | Evidence contradiction |
| Migration or persistence change | Opus + Human | Data integrity risk |
| Deployment required | Human | External-facing action |
| Destructive filesystem action | Human | Irreversible damage risk |
| Final merge candidate | Opus + Human | Governance gate |
