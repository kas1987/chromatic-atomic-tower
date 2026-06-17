# ID Crosswalk Template

Use this template to map grandfathered IDs to new naming format and routing hints.

| legacy_mission_id | new_mission_id | legacy_bead_id | new_bead_id | priority_tier | complexity_level | router_profile | preferred_worker_model | preferred_cheap_review_model | preferred_final_review_model | escalation_model | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| (net-new) | MP-CAT-A006-4C01 | (net-new) | BEAD-CAT-A006-4C01-01 | A | 4C | high_judgment | kimi-k2.7-code:cloud | minimax-m3:cloud | claude-opus-4-8 | claude-opus-4-8 | Canonical first post-cutover mission: tier A (frozen), global #006, complexity 4C. New beads keep BEAD- prefix (schema ^BEAD-); generators may emit BD-. |
