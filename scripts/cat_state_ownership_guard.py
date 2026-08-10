#!/usr/bin/env python3
"""Validate CAT's one-direction canonical-to-derived state ownership DAG."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "derived_state_ownership.schema.json"


def _normalize_path(path: str | None) -> str | None:
    """Use one separator form for all ownership comparisons and evidence."""
    return path.replace("\\", "/") if isinstance(path, str) else path


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _schema_errors(document: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    return [error.message for error in sorted(validator.iter_errors(document), key=str)]


def validate_ownership(document: dict) -> dict:
    """Return validity, rejection reasons, and ownership evidence.

    No conflict is resolved implicitly: any duplicate or inconsistent writer
    causes a rejection result.
    """

    errors = _schema_errors(document)
    facts = document.get("facts", [])
    fact_ids: set[str] = set()
    canonical_paths: dict[str, str] = {}
    derived_paths: dict[str, str] = {}
    derived_count = 0

    for fact in facts:
        fact_id = fact.get("fact_id")
        writer = fact.get("canonical_writer")
        canonical_path = _normalize_path(fact.get("canonical_path"))
        if fact_id in fact_ids:
            errors.append(f"duplicate fact_id: {fact_id}")
        fact_ids.add(fact_id)

        if canonical_path in canonical_paths:
            if canonical_paths[canonical_path] != writer:
                errors.append(
                    f"conflicting writers for canonical path {canonical_path}: "
                    f"{canonical_paths[canonical_path]} vs {writer}"
                )
            else:
                errors.append(f"duplicate canonical path: {canonical_path}")
        canonical_paths[canonical_path] = writer

        for artifact in fact.get("derived_artifacts", []):
            derived_count += 1
            path = _normalize_path(artifact.get("path"))
            artifact_writer = artifact.get("writer")
            source_fact = artifact.get("source_fact")
            if source_fact != fact_id:
                errors.append(
                    f"source_fact for {path} must match containing fact_id: "
                    f"{source_fact} vs {fact_id}"
                )
            if artifact_writer != writer:
                errors.append(
                    f"derived writer for {path} differs from canonical writer: "
                    f"{artifact_writer} vs {writer}"
                )
            if path in derived_paths:
                errors.append(f"duplicate derived path: {path}")
            derived_paths[path] = artifact_writer

    for path, writer in derived_paths.items():
        if path in canonical_paths:
            errors.append(f"derived artifact is also a canonical path: {path} ({writer})")
        if path in canonical_paths and canonical_paths[path] != writer:
            errors.append(f"conflicting writers for derived path {path}")

    valid = not errors
    return {
        "valid": valid,
        "errors": errors,
        "evidence": {
            "status": "valid" if valid else "rejected",
            "contract_version": document.get("contract_version"),
            "canonical_fact_count": len(facts),
            "derived_artifact_count": derived_count,
            "canonical_paths": sorted(path for path in canonical_paths if path),
            "derived_paths": sorted(path for path in derived_paths if path),
            "conflict_policy": "reject_without_writer_selection",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", required=True, type=Path)
    args = parser.parse_args(argv)
    document = json.loads(args.document.read_text(encoding="utf-8"))
    result = validate_ownership(document)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
