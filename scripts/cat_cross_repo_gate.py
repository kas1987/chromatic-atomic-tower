#!/usr/bin/env python3
"""Authorize bounded cross-repository mutation requests without executing them.

The gate is deliberately a pure decision surface. It validates the CAT trace,
checks that every concrete target is covered by a declared allowed pattern,
rejects CAT governance paths, and returns evidence for an authorized decision.
It never invokes a consumer repository or Harness V2.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "cross_repo_mutation.schema.json"

# These are CAT-owned governance paths. A consumer may return evidence about
# them, but an external mutation request may not target them.
CAT_PROTECTED_PREFIXES = (
    "missions/",
    "wiskers/",
    "archive/",
    ".beads/",
    "state/",
    "gates/",
    "agents/registry/",
    "learnings/",
)


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _schema_errors(request: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    return [error.message for error in sorted(validator.iter_errors(request), key=str)]


def _path_matches(path: str, pattern: str) -> bool:
    normalized_path = path.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    return normalized_path == normalized_pattern or fnmatch.fnmatchcase(
        normalized_path, normalized_pattern
    )


def _semantic_errors(request: dict) -> list[str]:
    errors: list[str] = []
    if not request.get("approved_by", "").strip():
        errors.append("human approval is required")

    allowed_paths = request.get("allowed_paths", [])
    for path in request.get("target_paths", []):
        normalized_path = path.replace("\\", "/")
        if any(
            normalized_path == prefix.rstrip("/") or normalized_path.startswith(prefix)
            for prefix in CAT_PROTECTED_PREFIXES
        ):
            errors.append(f"CAT-protected target path is not mutable: {path}")
        if not any(_path_matches(path, pattern) for pattern in allowed_paths):
            errors.append(f"target path is outside declared allowed_paths: {path}")
    return errors


def evaluate_request(request: dict) -> dict:
    """Return an authorization decision and traceable evidence for *request*."""

    errors = _schema_errors(request) + _semantic_errors(request)
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    decision_id = "MUT-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    allowed = not errors
    evidence = {
        "decision_id": decision_id,
        "status": "authorized" if allowed else "rejected",
        "mission_id": request.get("mission_id"),
        "bead_id": request.get("bead_id"),
        "target_repo": request.get("target_repo"),
        "operation": request.get("operation"),
        "target_paths": request.get("target_paths", []),
        "validation_command": request.get("validation_command"),
        "evidence_path": request.get("evidence_path"),
        "rollback_reference": request.get("rollback_reference"),
    }
    return {
        "allowed": allowed,
        "decision": "authorized" if allowed else "rejected",
        "errors": errors,
        "evidence": evidence,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = evaluate_request(request)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
