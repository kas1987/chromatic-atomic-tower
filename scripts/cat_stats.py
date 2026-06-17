#!/usr/bin/env python3
"""
cat_stats.py

Lightweight repo-health utility for the CAT repository.

Reads:
  - missions/registry/MISSION_REGISTRY.yaml
  - beads/active/*.yaml

Produces summary statistics about missions and active beads.
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List, Optional

import yaml


def _repo_root() -> str:
    """Return the repository root directory (parent of scripts/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _missions_path() -> str:
    return os.path.join(_repo_root(), "missions", "registry", "MISSION_REGISTRY.yaml")


def _beads_dir() -> str:
    return os.path.join(_repo_root(), "beads", "active")


def _count_by_status(items: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        status = item.get("status")
        if status is None:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def summarize() -> Dict[str, Any]:
    """
    Summarize mission registry and active bead YAMLs.

    Returns a dict with keys:
      - total_missions (int)
      - missions_by_status (dict str->int)
      - active_mission_id (str or None)
      - total_active_beads (int)
      - beads_by_status (dict str->int)
    """
    registry_path = _missions_path()
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Mission registry not found: {registry_path}")

    registry = _load_yaml(registry_path) or {}
    missions = registry.get("missions") or []
    active_mission_id = registry.get("active_mission_id")

    missions_by_status = _count_by_status(missions)

    beads_dir = _beads_dir()
    beads: List[Dict[str, Any]] = []
    if os.path.isdir(beads_dir):
        for bead_path in sorted(glob.glob(os.path.join(beads_dir, "*.yaml"))):
            try:
                bead = _load_yaml(bead_path) or {}
                if isinstance(bead, dict) and "bead_id" in bead and "status" in bead:
                    beads.append(bead)
            except yaml.YAMLError:
                # Skip malformed bead YAML files.
                continue

    beads_by_status = _count_by_status(beads)

    return {
        "total_missions": len(missions),
        "missions_by_status": missions_by_status,
        "active_mission_id": active_mission_id,
        "total_active_beads": len(beads),
        "beads_by_status": beads_by_status,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Print CAT repo mission and bead stats.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the summary as JSON.",
    )
    args = parser.parse_args(argv)

    try:
        summary = summarize()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Total missions: {summary['total_missions']}")
        print(f"Missions by status: {summary['missions_by_status']}")
        print(f"Active mission ID: {summary['active_mission_id']}")
        print(f"Total active beads: {summary['total_active_beads']}")
        print(f"Beads by status: {summary['beads_by_status']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
