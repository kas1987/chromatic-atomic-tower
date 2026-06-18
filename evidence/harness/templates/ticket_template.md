# Ticket: [ID] [Title]

## Priority
p1 / p2 / p3

## Objective

[One concrete outcome]

## Context

[Relevant architecture, prior decisions, constraints]

## Allowed Files

- `[path]`

## Blocked Actions

- Do not modify files outside allowed list.
- Do not change dependencies unless explicitly approved.
- Do not perform destructive actions.

## Required Commands

```bash
git diff --stat
# add repo-specific tests here
```

## Output Required

- Patch/diff
- Worker summary
- Command results
- Known risks

## Acceptance Criteria

- [criterion]
- [criterion]
- [criterion]

## Stop Conditions

Stop and report if:

- required files are missing
- tests fail after one fix attempt
- the task requires architectural decisions
- the change expands beyond allowed files
