# Missions

Missions define what work exists and what is allowed at the mission level.

Use `missions/templates/` to create new mission contracts.

Do not place active work outside `missions/active/` or `missions/registry/MISSION_REGISTRY.yaml`.

## Naming Convention (New Work)

- New mission IDs use: `MP-CAT-S001-4C01`
- `S|A|B|C` = priority tier (immutable after creation)
- `1C..4C` = complexity marker (`C` stands for complexity)
- New-work cutover applies to legacy numeric IDs at `MP-CAT-006` and above
- Legacy mission IDs below cutover remain valid and unchanged
