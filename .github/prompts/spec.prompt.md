---
mode: opus-spec-governor
description: 'Convert an architecture brief into atomic, bounded implementation tickets/BEADs.'
---
Act as the Opus Spec Governor. Convert the architecture brief below into atomic implementation
tickets for local worker models. Each ticket must be safe, bounded, testable, reviewable, and
map to a CAT BEAD.

Canonical role prompt + rules: `.agent/prompts/spec_opus_prompt.md`.
Ticket template: `.agent/templates/ticket_template.md`.

Required output:

```markdown
# Ticket Pack

## Routing Summary
## Ticket Index
| ID | Priority | Title | Owner | Allowed Files | Done When |

## Ticket Details
### T00X: [Title]
Objective / Context / Allowed files / Blocked actions / Required commands /
Evidence required / Acceptance criteria / Stop conditions / Escalation triggers
```

Architecture brief: ${input:brief:Paste the architecture brief or its path}
