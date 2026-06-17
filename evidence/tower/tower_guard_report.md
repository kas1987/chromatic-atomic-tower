# Tower Guard Report

Overall status: fail

## state_freshness

Status: fail

### OK
- active_mission_id matches: MP-CAT-004
- active mission file exists: missions\active\MP-CAT-004_V2_ALIGNMENT_GUARDS.yaml
- active BEAD file exists: beads\active\BEAD-CAT-004-004.yaml

### Issues
- active_bead_id mismatch: tower='BEAD-CAT-004-004' registry=None
- active BEAD BEAD-CAT-004-004 has status='archived', expected "active"

## branch_root_hygiene

Status: pass

### OK
- branch is hygienic: fix/test-isolation-health-2026-06-17
- root entries satisfy hygiene allowlist
