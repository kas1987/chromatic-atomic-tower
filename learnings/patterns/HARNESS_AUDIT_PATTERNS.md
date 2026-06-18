# Harness Audit Patterns

## Pattern: Completeness before correctness

A technically correct output can still fail if the mission was incomplete.

## Pattern: Controls and substantive validation are separate

Passing process controls does not prove the work product works.

## Pattern: Evidence over narrative

Confidence must be calculated from artifacts, tests, logs, diffs, reviews, and gate results.

## Pattern: Route by risk, not ego

Use the lowest sufficient model, but escalate when evidence shows the route is insufficient.

## Pattern: Single writer per working tree

Concurrent agents on one git working tree corrupt provenance and lose work. Isolate with git
worktrees; integrate via PR. (Source: 2026-06-17 Codex/VS Code collision — see DECISION_LOG.)
