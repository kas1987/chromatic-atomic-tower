#!/usr/bin/env python3
"""
cat_transition.py — CAT state-machine transition engine (BEAD-CAT-001-002).

Loads canonical rules from gates/state/transition_rules.yaml, validates the
requested (from, to) arc, evaluates its guard, and in execute mode atomically
mutates the target YAML file.

Usage:
  cat_transition.py (--dry-run | --execute) \
      (--mission <id> | --bead <id>) \
      --from <state> --to <state> [--reason TEXT]

Exit codes:
  0  success (dry-run validated or execute applied)
  1  transition rejected (invalid arc or guard failure)
  2  usage / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
from common import load_yaml, write_yaml, rel  # noqa: E402

RULES_PATH = ROOT / "gates" / "state" / "transition_rules.yaml"
REGISTRY_PATH = ROOT / "missions" / "registry" / "MISSION_REGISTRY.yaml"
EVIDENCE_LOG = ROOT / "evidence" / "logs" / "transitions.jsonl"

# ---------------------------------------------------------------------------
# Rule lookup
# ---------------------------------------------------------------------------


def load_rules() -> dict:
    return load_yaml(RULES_PATH)


def find_rule(rules: dict, entity_type: str, from_state: str, to_state: str) -> dict | None:
    key = "mission_transitions" if entity_type == "mission" else "bead_transitions"
    for rule in rules.get(key, []):
        if rule["from"] == from_state and rule["to"] == to_state:
            return rule
    return None


# ---------------------------------------------------------------------------
# Entity lookup
# ---------------------------------------------------------------------------


def _registry_mission(registry: dict, mission_id: str) -> dict | None:
    for m in registry.get("missions", []):
        if m.get("mission_id") == mission_id:
            return m
    return None


def _find_bead_yaml(bead_id: str) -> Path | None:
    for candidate in ROOT.glob(f"beads/**/{bead_id}.yaml"):
        return candidate
    return None


def _find_mission_yaml(mission_id: str, registry: dict) -> Path | None:
    entry = _registry_mission(registry, mission_id)
    if not entry or not entry.get("path"):
        return None
    p = ROOT / entry["path"]
    return p if p.exists() else None


# ---------------------------------------------------------------------------
# Guard evaluation
# ---------------------------------------------------------------------------

# Guards not yet implemented are skipped with a warning so they don't block
# early callers.  Full evaluation is BEAD-CAT-001-003's responsibility.
_DEFERRED_GUARDS = {
    "evidence_present",
    "validation_passed",
    "review_gate_pass",
    "escalation_ack",
    "closeout_complete",
    "rollback_plan_present",
}


def evaluate_guard(
    guard_name: str,
    entity_type: str,
    entity_id: str,
    registry: dict,
) -> tuple[bool, str]:
    """Return (passed, message)."""

    if guard_name == "none":
        return True, "no precondition"

    if guard_name == "active_bead_present":
        # Mission-only guard: current_bead_id must be set and the file must exist.
        entry = _registry_mission(registry, entity_id)
        bead_id = entry.get("current_bead_id") if entry else None
        if not bead_id:
            return False, "mission has no current_bead_id"
        bead_path = _find_bead_yaml(bead_id)
        if not bead_path:
            return False, f"current_bead_id={bead_id!r} not found on disk"
        return True, f"current_bead_id={bead_id}"

    if guard_name == "human_gate_if_required":
        mission_id = entity_id if entity_type == "mission" else None
        if mission_id:
            mission_yaml = _find_mission_yaml(mission_id, registry)
            if mission_yaml:
                try:
                    mission = load_yaml(mission_yaml)
                    hg = mission.get("human_gate", {})
                    if not hg.get("required", False):
                        return True, "human_gate.required=false"
                    approver = hg.get("approver")
                    if approver:
                        return True, f"approver={approver!r}"
                    return False, "human_gate.required=true but no approver recorded"
                except Exception as exc:
                    return True, f"skip (could not read mission YAML: {exc})"
        return True, "skip (mission file unavailable)"

    if guard_name in _DEFERRED_GUARDS:
        return True, f"skip (guard evaluation deferred to BEAD-CAT-001-003)"

    return False, f"unknown guard {guard_name!r}"


# ---------------------------------------------------------------------------
# State reading
# ---------------------------------------------------------------------------


def read_current_state(entity_type: str, entity_id: str, registry: dict) -> str | None:
    if entity_type == "mission":
        entry = _registry_mission(registry, entity_id)
        return entry.get("status") if entry else None
    else:
        bead_path = _find_bead_yaml(entity_id)
        if not bead_path:
            return None
        try:
            return load_yaml(bead_path).get("status")
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Atomic write helpers
# ---------------------------------------------------------------------------


def _write_atomic(path: Path, data: dict) -> None:
    """Write data to a temp file in the same directory, then rename."""
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, suffix=".tmp", delete=False
    ) as tf:
        tmp_path = Path(tf.name)
    try:
        write_yaml(tmp_path, data)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def apply_mission_transition(
    entity_id: str, from_state: str, to_state: str, registry: dict
) -> dict:
    """Return an updated registry dict (does not write)."""
    now = datetime.now(timezone.utc).isoformat()
    updated_missions = []
    found = False
    for m in registry.get("missions", []):
        if m.get("mission_id") == entity_id:
            if m.get("status") != from_state:
                raise ValueError(
                    f"registry shows {entity_id} as {m['status']!r}, not {from_state!r}"
                )
            updated_missions.append({**m, "status": to_state, "last_updated": now})
            found = True
        else:
            updated_missions.append(m)
    if not found:
        raise ValueError(f"mission {entity_id!r} not found in registry")
    return {**registry, "missions": updated_missions, "last_updated": now}


def apply_bead_transition(
    entity_id: str, from_state: str, to_state: str
) -> Path:
    """Mutate the BEAD YAML file atomically. Returns the path written."""
    bead_path = _find_bead_yaml(entity_id)
    if not bead_path:
        raise ValueError(f"BEAD file for {entity_id!r} not found")
    bead = load_yaml(bead_path)
    if bead.get("status") != from_state:
        raise ValueError(
            f"BEAD file shows {entity_id} as {bead['status']!r}, not {from_state!r}"
        )
    now = datetime.now(timezone.utc).isoformat()
    updated = {**bead, "status": to_state, "last_updated": now}
    _write_atomic(bead_path, updated)
    return bead_path


# ---------------------------------------------------------------------------
# Evidence logging
# ---------------------------------------------------------------------------


def log_evidence(record: dict) -> None:
    EVIDENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CAT state-machine transition engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="validate transition without mutating any file")
    mode.add_argument("--execute", action="store_true",
                      help="validate and apply the transition atomically")

    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--mission", metavar="ID", help="mission ID (MP-…)")
    target.add_argument("--bead", metavar="ID", help="BEAD ID (BEAD-…)")

    p.add_argument("--from", dest="from_state", required=True, metavar="STATE",
                   help="expected current state")
    p.add_argument("--to", dest="to_state", required=True, metavar="STATE",
                   help="target state")
    p.add_argument("--reason", default="", metavar="TEXT",
                   help="human-readable reason recorded in the evidence log")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    entity_type = "mission" if args.mission else "bead"
    entity_id = args.mission or args.bead
    from_state = args.from_state
    to_state = args.to_state
    mode = "dry-run" if args.dry_run else "execute"

    # Load rules
    try:
        rules = load_rules()
    except Exception as exc:
        print(f"ERROR: could not load transition rules: {exc}", file=sys.stderr)
        sys.exit(2)

    # Validate the arc exists
    rule = find_rule(rules, entity_type, from_state, to_state)
    if not rule:
        print(
            f"ERROR: {entity_type} transition {from_state!r} ->{to_state!r} is not "
            "defined in transition_rules.yaml",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load registry (needed for both mission and BEAD guard evaluation)
    try:
        registry = load_yaml(REGISTRY_PATH)
    except Exception as exc:
        print(f"ERROR: could not load registry: {exc}", file=sys.stderr)
        sys.exit(2)

    # Verify the entity's current state matches --from
    actual_state = read_current_state(entity_type, entity_id, registry)
    if actual_state is None:
        print(f"ERROR: {entity_type} {entity_id!r} not found", file=sys.stderr)
        sys.exit(1)
    if actual_state != from_state:
        print(
            f"ERROR: {entity_id} is currently {actual_state!r}, not {from_state!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Evaluate guard
    guard_name = rule["guard"]
    guard_passed, guard_msg = evaluate_guard(guard_name, entity_type, entity_id, registry)

    # Print summary
    print(f"transition : {entity_type} {entity_id}  {from_state} ->{to_state}")
    print(f"  rule     : reversible={rule['reversible']}")
    print(f"  guard    : {guard_name}  -> {'PASS' if guard_passed else 'FAIL'} ({guard_msg})")

    # Base evidence record
    record: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "from": from_state,
        "to": to_state,
        "guard": guard_name,
        "guard_result": "pass" if guard_passed else "fail",
        "guard_message": guard_msg,
        "reversible": rule.get("reversible", False),
        "reason": args.reason,
        "actor": "cat_transition.py",
    }

    if not guard_passed:
        print(f"\nERROR: guard {guard_name!r} failed — {guard_msg}", file=sys.stderr)
        record["outcome"] = "rejected"
        log_evidence(record)
        sys.exit(1)

    if mode == "dry-run":
        print(f"\n[dry-run] would set {entity_id}.status  {from_state!r} ->{to_state!r}")
        if entity_type == "mission":
            print(f"[dry-run] target file : {rel(REGISTRY_PATH)}")
        else:
            bead_path = _find_bead_yaml(entity_id)
            print(f"[dry-run] target file : {rel(bead_path) if bead_path else '(not found)'}")
        print(f"[dry-run] evidence log: {rel(EVIDENCE_LOG)}")
        record["outcome"] = "dry-run"
        log_evidence(record)
        sys.exit(0)

    # Execute mode
    try:
        if entity_type == "mission":
            updated_registry = apply_mission_transition(
                entity_id, from_state, to_state, registry
            )
            _write_atomic(REGISTRY_PATH, updated_registry)
            print(f"\n[execute] {entity_id}.status = {to_state!r}  ({rel(REGISTRY_PATH)} updated)")
        else:
            bead_path = apply_bead_transition(entity_id, from_state, to_state)
            print(f"\n[execute] {entity_id}.status = {to_state!r}  ({rel(bead_path)} updated)")
    except Exception as exc:
        print(f"ERROR: transition failed: {exc}", file=sys.stderr)
        record["outcome"] = "error"
        log_evidence(record)
        sys.exit(1)

    record["outcome"] = "applied"
    log_evidence(record)
    print(f"[execute] evidence log: {rel(EVIDENCE_LOG)}")


if __name__ == "__main__":
    main()
