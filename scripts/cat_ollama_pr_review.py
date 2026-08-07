#!/usr/bin/env python3
"""CAT Ollama PR review artifact scaffold.

Writes JSON under ``evidence/reviews/pr-{N}.json``. Dry-run mode writes an
attested-shaped artifact without calling a live Ollama endpoint.

Env:
  OLLAMA_HOST (default http://127.0.0.1:11434)
  CAT_OLLAMA_ATTESTATION_KEY (optional HMAC key)

Not a required CI check.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REVIEWS_DIR = ROOT / "evidence" / "reviews"

ARTIFACT_ATTESTATION_VERSION = "hmac-sha256-v1"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "kimi-k2.7-code:cloud"


def _attestation_key() -> bytes | None:
    raw = os.environ.get("CAT_OLLAMA_ATTESTATION_KEY", "")
    return raw.encode("utf-8") if raw else None


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in payload.items() if key != "attestation"}
    return json.dumps(
        unsigned, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def attest_payload(payload: dict[str, Any], *, dry_run: bool = False) -> Any:
    """Return HMAC attestation dict, or the string ``dry-run`` / placeholder."""
    if dry_run and not _attestation_key():
        return "dry-run"
    key = _attestation_key()
    if not key:
        return "unattested"
    canonical = _canonical_payload(payload)
    return {
        "version": ARTIFACT_ATTESTATION_VERSION,
        "payload_sha256": hashlib.sha256(canonical).hexdigest(),
        "signature": hmac.new(key, canonical, hashlib.sha256).hexdigest(),
        "key_id": os.environ.get("CAT_OLLAMA_ATTESTATION_KEY_ID", "local-operator"),
    }


def artifact_path(pr: int, reviews_dir: Path | None = None) -> Path:
    root = reviews_dir or REVIEWS_DIR
    return root / f"pr-{pr}.json"


def write_review_artifact(
    *,
    pr: int,
    head_sha: str,
    model: str,
    summary: str = "scaffold dry-run review",
    dry_run: bool = False,
    reviews_dir: Path | None = None,
) -> Path:
    """Write attested-shaped JSON artifact; create parent dir if needed."""
    path = artifact_path(pr, reviews_dir=reviews_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "pr": pr,
        "head_sha": head_sha,
        "model": model,
        "provider": "ollama",
        "summary": summary,
        "dry_run": dry_run,
        "ollama_host": os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
    }
    payload["attestation"] = attest_payload(payload, dry_run=dry_run)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write a CAT Ollama PR review artifact under evidence/reviews/. "
            "Use --dry-run to skip live Ollama calls."
        )
    )
    parser.add_argument("--pr", type=int, required=True, help="Pull request number.")
    parser.add_argument("--head-sha", required=True, help="PR head commit SHA.")
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL),
        help=f"Model tag (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Review summary text (default scaffold text in dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write scaffold artifact without calling live Ollama.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Override evidence/reviews output directory (tests).",
    )
    args = parser.parse_args(argv)

    if not args.dry_run:
        # Live Ollama path is intentionally stubbed in Phase 2.
        print(
            json.dumps(
                {
                    "error": "live Ollama call not implemented in Phase 2 scaffold; use --dry-run",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    reviews_dir = Path(args.out_dir) if args.out_dir else None
    summary = args.summary or "scaffold dry-run review"
    path = write_review_artifact(
        pr=args.pr,
        head_sha=args.head_sha,
        model=args.model,
        summary=summary,
        dry_run=True,
        reviews_dir=reviews_dir,
    )
    print(json.dumps({"path": str(path), "provider": "ollama", "pr": args.pr}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
