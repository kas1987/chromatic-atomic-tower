# CAT State Transition Playbook

## Purpose

This playbook governs how missions and BEADs move through lifecycle states.

## Required Inputs

- Target type: mission or BEAD
- Target ID
- Current status
- Requested target status
- Reason
- Evidence path when required
- Actor

## Decision Loop

```text
Read contract -> Read rules -> Check transition -> Check evidence -> Dry-run -> Apply -> Audit -> Validate -> Queue next
```

## Allowed Agent Behavior

Agents may propose transitions and run dry-runs. Agents may apply transitions only inside the active mission scope and only when confidence is at least the configured minimum.

## Stop Conditions

- Unknown current status
- Unknown target status
- Target state requires evidence and no evidence is provided
- Terminal state reopening requested
- Registry and contract mismatch
- Human gate is required

## Review Rule

A transition to `completed`, `closed`, or `learned` should include evidence that would satisfy an outside reviewer.
