# Mission Packet Playbook

## Purpose

Define how CAT creates, reviews, approves, and maintains Mission Packs.

## Required mission fields

- mission_id
- title
- level
- status
- owner
- priority
- risk_level
- reversibility
- autonomy_level
- confidence_minimum
- objective
- scope
- allowed_paths
- forbidden_paths
- acceptance_criteria
- required_validation
- rollback
- human_gate
- tool_budget
- beads
- evidence_requirements

## Review checklist

Before approval, confirm:

- complexity level fits
- scope is bounded
- allowed paths are explicit
- rollback exists if needed
- validation is possible
- dependencies are known
- human gate is correct

## Approval rule

M1 and M2 may be approved by owner or orchestrator if reversible.

M3 requires reviewer or architect review.

M4 requires formal human approval.
