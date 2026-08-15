# Legacy CAT State Archive

This directory is a read-only historical archive of CAT's pre-cutover operational
state. It is preserved for audit, learning, and rollback analysis only.

The archived `beads/` tree contains CAT's former YAML contract system, including
historical `BEAD-CAT-*` records, templates, examples, and completion/failure
ledgers. Those IDs remain unchanged here by design. They are not official Beads
issues and must never be selected, claimed, dispatched, or closed by runtime CAT
code.

The archived mission registry and A019/A020 evidence record the state that existed
before the Official Beads + Wiskers cutover. The authoritative post-cutover
sources are:

- `.beads/` — the local Official Beads/Dolt database (ignored from the source tree)
- `wiskers/` — CAT-owned scoped execution packets derived from official Beads
- `missions/registry/MISSION_REGISTRY.yaml` — active CAT mission index
- `state/TOWER_STATE.yaml` — CAT operator state

Do not add runtime readers for this archive. Any recovery or comparison workflow
must state explicitly that it is reading historical material.
