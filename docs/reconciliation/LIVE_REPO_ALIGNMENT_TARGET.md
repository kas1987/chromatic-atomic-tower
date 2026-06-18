# Live Repo Alignment Target

This document summarizes the target state encoded in `LIVE_REPO_ALIGNMENT_TARGET.yaml`.

## Active Mission

`MP-CAT-A011-4C01` — Agent Scorecard Automation (tower is `sprint_active`, SPRINT-011).

## Next Mission

`MP-CAT-A012-4C01` — CAT Portable Project Adapter

## Required Sprint Truth

Sprints 000 through 010 must be represented in `missions/registry/MISSION_REGISTRY.yaml` with their final statuses (`closed` or `learned`). Mission A011 must be present as `approved`. Backlog mission A012 must exist as a draft scaffold.

## Rule

```text
No Reconciled Registry = No New Sprint
```
