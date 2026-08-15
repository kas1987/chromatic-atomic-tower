# Pre-cutover CAT tests

These tests are preserved from the custom YAML `BEAD-CAT-*` execution plane.
They are retained for historical comparison and migration forensics, but are
not part of the active test target because they assert lifecycle behavior that
CAT intentionally removed during the Official Beads + Wiskers cutover.

The active suite is under `tests/` and covers the authoritative `bd`/Dolt
adapter, deterministic selection, Wisker schema and digest pinning, fail-closed
behavior, evidence-first closeout, and the absence of legacy runtime reads.
