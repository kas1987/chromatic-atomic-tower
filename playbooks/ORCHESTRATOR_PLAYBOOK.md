# Orchestrator Playbook

| Field | Value |
|---|---|
| Status | Active Baseline |
| Version | 0.0.0 |
| Applies To | GO-mode and dispatch |

## Purpose

The Orchestrator turns intent into one controlled next action.

## Standard loop

```text
Read state -> Select mission -> Select BEAD -> Check gates -> Dispatch -> Record result
```

## Required inputs

- `state/TOWER_STATE.yaml`
- `missions/registry/MISSION_REGISTRY.yaml`
- active BEAD file
- agent registry
- confidence gate

## Dispatch rule

Dispatch only if:

- mission status is approved, dispatched, in_progress, or validating
- BEAD status is active or queued
- confidence is at or above minimum
- human gate is not required or has approval
- allowed paths and forbidden paths are clear

## Forbidden behavior

- broad repo exploration
- inventing new work
- skipping confidence gate
- dispatching multiple agents without M4 governance
