# Agent Promotion Rules

Agents earn autonomy. They do not assume it.

## Promotion signals

- completes 5 BEADs cleanly
- respects tool budgets
- passes review without rework
- produces evidence consistently
- avoids forbidden paths

## Demotion signals

- touches forbidden paths
- exceeds tool budget repeatedly
- skips validation
- closes work without evidence
- mutates state below confidence threshold
- causes incident

## Promotion table

| Current | Promotion target | Required evidence |
|---|---|---|
| L1 | L2 | 3 clean planning or review BEADs |
| L2 | L3 | 5 clean scoped BEADs |
| L3 | L4 | 8 clean BEADs plus auditor approval |
| L4 | L5 | Human approval only |
