#!/usr/bin/env python3
"""CAT review coverage scaffold — provider allowlist and dual-LLM quorum.

Minimal Phase 2 stub adapted from DataAnn ``tools/review_coverage.py``.
Does not call GitHub APIs; does not make Ollama a required CI check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REVIEW_LEVELS = ("R0", "R1", "R2", "R3", "R4")

PROVIDER_CODEX = "codex"
PROVIDER_COPILOT = "copilot"
PROVIDER_OLLAMA = "ollama"

LLM_PROVIDERS = frozenset({PROVIDER_CODEX, PROVIDER_COPILOT, PROVIDER_OLLAMA})

# Exact identity allowlist (human logins never count as seats).
REVIEWER_ALLOWLIST: dict[str, frozenset[str]] = {
    PROVIDER_CODEX: frozenset({"chatgpt-codex-connector"}),
    PROVIDER_COPILOT: frozenset(
        {"copilot-pull-request-reviewer", "github-copilot[bot]"}
    ),
    # Ollama seat is artifact-backed, not a GitHub login.
    PROVIDER_OLLAMA: frozenset({"ollama-artifact"}),
}


def normalize_review_level(value: str | None) -> str:
    raw = (value or "R2").strip().upper()
    if raw in REVIEW_LEVELS:
        return raw
    return "R2"


def seat_from_author(author: str) -> str | None:
    """Map a GitHub login to an allowlisted LLM provider seat, or None."""
    login = (author or "").strip().casefold()
    if not login:
        return None
    for seat, identities in REVIEWER_ALLOWLIST.items():
        if login in identities:
            return seat
    return None


def is_allowlisted_author(author: str) -> bool:
    return seat_from_author(author) is not None


def provider_in_allowlist(provider: str) -> bool:
    return (provider or "").strip().casefold() in LLM_PROVIDERS


def quorum_needed_for_level(level: str) -> int:
    """R0/R1/R2 require dual-LLM seats; R3/R4 require one."""
    normalized = normalize_review_level(level)
    if normalized in {"R0", "R1", "R2"}:
        return 2
    return 1


def evaluate_quorum(providers_present: list[str] | set[str], level: str) -> bool:
    """Return True when distinct allowlisted providers meet the level quorum."""
    unique = {
        p.strip().casefold()
        for p in providers_present
        if isinstance(p, str) and p.strip().casefold() in LLM_PROVIDERS
    }
    return len(unique) >= quorum_needed_for_level(level)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CAT review coverage scaffold: provider allowlist and dual-LLM quorum. "
            "Advisory only — not a required CI check."
        )
    )
    parser.add_argument(
        "--check-quorum",
        action="store_true",
        help="Evaluate whether providers meet quorum for --level.",
    )
    parser.add_argument(
        "--level",
        default="R2",
        help="Review level R0–R4 (default: R2).",
    )
    parser.add_argument(
        "--providers",
        default="",
        help="Comma-separated providers present (codex,copilot,ollama).",
    )
    args = parser.parse_args(argv)

    if args.check_quorum:
        providers = [p.strip() for p in args.providers.split(",") if p.strip()]
        level = normalize_review_level(args.level)
        needed = quorum_needed_for_level(level)
        met = evaluate_quorum(providers, level)
        payload = {
            "level": level,
            "providers": providers,
            "quorum_needed": needed,
            "quorum_met": met,
        }
        print(json.dumps(payload, indent=2))
        return 0 if met else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
