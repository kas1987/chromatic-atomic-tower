#!/usr/bin/env python3
"""
cat_transition.py — CAT state-machine transition engine (BEAD-CAT-001-002/003).

Loads canonical rules from gates/state/transition_rules.yaml, validates the
requested (from, to) arc, evaluates its guard, and in execute mode creates a
pre-transition snapshot then atomically mutates the target YAML file.

Usage:
  cat_transition.py (--dry-run | --execute) \
      (--mission <id> | --bead <id>) \
      --from <state> --to <state> [--reason TEXT]

  cat_transition.py --rollback <snapshot_id> [--reason TEXT]

Exit codes:
  0  success (dry-run validated, execute applied, or rollback restored)
  1  transition rejected (invalid arc, guard failure, or snapshot not found)
  2  usage / IO error
"""

from __future__ import annotations

import argparse
import json
import shutil
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
TRANSITION_LOG = ROOT / "evidence" / "transitions" / "transition_log.jsonl"
SNAPSHOTS_DIR = ROOT / "evidence" / "snapshots"
ROLLBACKS_DIR = ROOT / "evidence" / "rollbacks"

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

# Guards not yet fully implemented skip with a warning rather than blocking.
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
        return True, "skip (guard evaluation deferred to BEAD-CAT-001-004)"

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
# Atomic write helper
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


# ---------------------------------------------------------------------------
# Snapshot creation
# ---------------------------------------------------------------------------


def _snapshot_id(now: datetime) -> str:
    """Return a filesystem-safe snapshot ID from a UTC datetime."""
    return "snap_" + now.strftime("%Y%m%dT%H%M%SZ")


def _files_to_snapshot(entity_type: str, entity_id: str) -> list[Path]:
    """Return the list of files that must be captured before a transition."""
    files = [REGISTRY_PATH]
    if entity_type == "bead":
        bead_path = _find_bead_yaml(entity_id)
        if bead_path:
            files.append(bead_path)
    # Include any YAML files under a top-level state/ directory if it exists.
    state_dir = ROOT / "state"
    if state_dir.is_dir():
        files.extend(state_dir.rglob("*.yaml"))
    return [p for p in files if p.exists()]


def create_snapshot(
    entity_type: str,
    entity_id: str,
    from_state: str,
    to_state: str,
    now: datetime,
) -> tuple[str, Path]:
    """
    Copy mutable state files into evidence/snapshots/<snapshot_id>/.
    Write metadata.json inside the snapshot directory.
    Append a record to evidence/transitions/transition_log.jsonl.
    Returns (snapshot_id, snapshot_dir).
    """
    snap_id = _snapshot_id(now)
    snap_dir = SNAPSHOTS_DIR / snap_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    source_files = _files_to_snapshot(entity_type, entity_id)
    captured: list[dict] = []
    for src in source_files:
        dest_name = src.name
        dest = snap_dir / dest_name
        # Avoid name collision when multiple files share a basename.
        if dest.exists():
            dest = snap_dir / f"{src.parent.name}_{src.name}"
        shutil.copy2(src, dest)
        captured.append({"original": rel(src), "snapshot": dest.name})

    metadata = {
        "snapshot_id": snap_id,
        "timestamp": now.isoformat(),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "from_state": from_state,
        "to_state": to_state,
        "files": captured,
    }
    (snap_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    _append_transition_log({
        "event": "snapshot_created",
        "snapshot_id": snap_id,
        "timestamp": now.isoformat(),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "from_state": from_state,
        "to_state": to_state,
    })

    return snap_id, snap_dir


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def _load_snapshot_metadata(snapshot_id: str) -> tuple[dict, Path]:
    snap_dir = SNAPSHOTS_DIR / snapshot_id
    meta_path = snap_dir / "metadata.json"
    if not snap_dir.is_dir() or not meta_path.exists():
        raise FileNotFoundError(f"snapshot {snapshot_id!r} not found at {rel(snap_dir)}")
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"could not parse snapshot metadata: {exc}") from exc
    return metadata, snap_dir


def restore_snapshot(snapshot_id: str, reason: str) -> list[str]:
    """
    Atomically restore every file listed in the snapshot's metadata.
    Writes a rollback evidence record to evidence/rollbacks/.
    Returns a list of restored file paths (relative).
    """
    metadata, snap_dir = _load_snapshot_metadata(snapshot_id)
    now = datetime.now(timezone.utc)

    restored: list[str] = []
    errors: list[str] = []
    for entry in metadata.get("files", []):
        original_rel = entry["original"]
        snapshot_file = snap_dir / entry["snapshot"]
        original_abs = ROOT / original_rel

        if not snapshot_file.exists():
            errors.append(f"snapshot file missing: {entry['snapshot']}")
            continue

        try:
            original_abs.parent.mkdir(parents=True, exist_ok=True)
            # Copy snapshot content, then touch last_updated in YAML files.
            data = load_yaml(snapshot_file)
            if isinstance(data, dict):
                data["last_updated"] = now.isoformat()
            _write_atomic(original_abs, data)
            restored.append(original_rel)
        except Exception as exc:
            errors.append(f"{original_rel}: {exc}")

    if errors:
        raise RuntimeError("rollback partially failed:\n  " + "\n  ".join(errors))

    # Write rollback evidence record.
    rollback_record = {
        "snapshot_id": snapshot_id,
        "timestamp": now.isoformat(),
        "entity_type": metadata.get("entity_type"),
        "entity_id": metadata.get("entity_id"),
        "original_from": metadata.get("from_state"),
        "original_to": metadata.get("to_state"),
        "restored_files": restored,
        "reason": reason,
        "actor": "cat_transition.py",
    }
    ROLLBACKS_DIR.mkdir(parents=True, exist_ok=True)
    rollback_path = ROLLBACKS_DIR / f"{snapshot_id}.jsonl"
    with rollback_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rollback_record, ensure_ascii=False) + "\n")

    _append_transition_log({
        "event": "rollback_applied",
        "snapshot_id": snapshot_id,
        "timestamp": now.isoformat(),
        "entity_type": metadata.get("entity_type"),
        "entity_id": metadata.get("entity_id"),
        "restored_files": restored,
        "reason": reason,
    })

    return restored


# ---------------------------------------------------------------------------
# Transition helpers
# ---------------------------------------------------------------------------


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


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_evidence(record: dict) -> None:
    _append_jsonl(EVIDENCE_LOG, record)


def _append_transition_log(record: dict) -> None:
    _append_jsonl(TRANSITION_LOG, record)


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
                      help="validate, snapshot, and apply the transition atomically")
    mode.add_argument("--rollback", metavar="SNAPSHOT_ID",
                      help="restore files from a previous snapshot")

    target = p.add_mutually_exclusive_group()
    target.add_argument("--mission", metavar="ID", help="mission ID (MP-...)")
    target.add_argument("--bead", metavar="ID", help="BEAD ID (BEAD-...)")

    p.add_argument("--from", dest="from_state", metavar="STATE",
                   help="expected current state (required for --dry-run / --execute)")
    p.add_argument("--to", dest="to_state", metavar="STATE",
                   help="target state (required for --dry-run / --execute)")
    p.add_argument("--reason", default="", metavar="TEXT",
                   help="human-readable reason recorded in the evidence log")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Rollback path
    # ------------------------------------------------------------------
    if args.rollback:
        snapshot_id = args.rollback
        print(f"rollback  : {snapshot_id}")
        try:
            restored = restore_snapshot(snapshot_id, args.reason)
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"ERROR: rollback failed: {exc}", file=sys.stderr)
            sys.exit(1)
        for f in restored:
            print(f"  restored: {f}")
        print(f"  evidence: {rel(ROLLBACKS_DIR / (snapshot_id + '.jsonl'))}")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Transition path — validate required args
    # ------------------------------------------------------------------
    if not args.mission and not args.bead:
        parser.error("one of --mission / --bead is required for --dry-run / --execute")
    if not args.from_state:
        parser.error("--from is required for --dry-run / --execute")
    if not args.to_state:
        parser.error("--to is required for --dry-run / --execute")

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

    # Load registry
    try:
        registry = load_yaml(REGISTRY_PATH)
    except Exception as exc:
        print(f"ERROR: could not load registry: {exc}", file=sys.stderr)
        sys.exit(2)

    # Verify current state
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
        print(f"\nERROR: guard {guard_name!r} failed -- {guard_msg}", file=sys.stderr)
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

    # Execute mode: snapshot first, then mutate.
    now = datetime.now(timezone.utc)
    try:
        snap_id, snap_dir = create_snapshot(entity_type, entity_id, from_state, to_state, now)
        print(f"\n[execute] snapshot   : {snap_id}  ({rel(snap_dir)})")
    except Exception as exc:
        print(f"ERROR: could not create snapshot: {exc}", file=sys.stderr)
        record["outcome"] = "error"
        log_evidence(record)
        sys.exit(1)

    record["snapshot_id"] = snap_id

    try:
        if entity_type == "mission":
            updated_registry = apply_mission_transition(
                entity_id, from_state, to_state, registry
            )
            _write_atomic(REGISTRY_PATH, updated_registry)
            print(f"[execute] {entity_id}.status = {to_state!r}  ({rel(REGISTRY_PATH)} updated)")
        else:
            bead_path = apply_bead_transition(entity_id, from_state, to_state)
            print(f"[execute] {entity_id}.status = {to_state!r}  ({rel(bead_path)} updated)")
    except Exception as exc:
        print(f"ERROR: transition failed: {exc}", file=sys.stderr)
        print(f"       snapshot preserved at {rel(snap_dir)} -- rollback with:", file=sys.stderr)
        print(f"       cat_transition.py --rollback {snap_id}", file=sys.stderr)
        record["outcome"] = "error"
        log_evidence(record)
        sys.exit(1)

    record["outcome"] = "applied"
    log_evidence(record)
    print(f"[execute] evidence log: {rel(EVIDENCE_LOG)}")
    print(f"[execute] rollback via: cat_transition.py --rollback {snap_id}")


if __name__ == "__main__":
    main()
