# CAT Risk Register — Sprint 001

| Risk | Level | Mitigation | Owner |
|---|---:|---|---|
| Invalid transition mutates registry | High | Dry-run default available; tests cover denied transitions | Builder |
| BEAD completed without evidence | Medium | Transition rules require evidence for review/completed states | Auditor |
| Terminal status reopened casually | High | Terminal states deny outgoing transitions by default | Orchestrator |
| Mission and tower state drift | Medium | `cat_transition.py` updates registry and tower state together | Builder |
| Script touches wrong file | Medium | Search by mission_id / bead_id and path constraints | Reviewer |
