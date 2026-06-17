# Tool Budget Playbook

## Purpose

Prevent tool-call explosions and wandering.

## Budget fields

- search
- read
- write
- execute
- max_runtime_minutes

## Enforcement

Agents should self-track tool usage in their result block.

If budget is exceeded, the agent must stop and report:

- what was attempted
- why budget was insufficient
- what decision is needed
