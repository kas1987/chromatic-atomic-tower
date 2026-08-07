"""Phase 2 scaffold tests for CAT review coverage and Ollama artifact stubs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / "scripts"))

from cat_ollama_pr_review import write_review_artifact  # noqa: E402
from cat_review_coverage import (  # noqa: E402
    LLM_PROVIDERS,
    REVIEWER_ALLOWLIST,
    evaluate_quorum,
    is_allowlisted_author,
    provider_in_allowlist,
    quorum_needed_for_level,
    seat_from_author,
)


@pytest.mark.parametrize(
    ("level", "needed"),
    [
        ("R0", 2),
        ("R1", 2),
        ("R2", 2),
        ("R3", 1),
        ("R4", 1),
    ],
)
def test_quorum_needed_for_level(level: str, needed: int) -> None:
    assert quorum_needed_for_level(level) == needed


def test_evaluate_quorum_r2_requires_two_distinct_providers() -> None:
    assert evaluate_quorum(["codex"], "R2") is False
    assert evaluate_quorum(["codex", "codex"], "R2") is False
    assert evaluate_quorum(["codex", "ollama"], "R2") is True
    assert evaluate_quorum(["codex", "copilot", "ollama"], "R2") is True


def test_evaluate_quorum_r3_requires_one() -> None:
    assert evaluate_quorum([], "R3") is False
    assert evaluate_quorum(["ollama"], "R3") is True
    assert evaluate_quorum(["codex"], "R4") is True


def test_evaluate_quorum_ignores_unknown_providers() -> None:
    assert evaluate_quorum(["human", "alice"], "R2") is False
    assert evaluate_quorum(["human", "codex", "copilot"], "R2") is True


def test_provider_allowlist_membership() -> None:
    assert LLM_PROVIDERS == frozenset({"codex", "copilot", "ollama"})
    assert provider_in_allowlist("codex")
    assert provider_in_allowlist("COPILOT")
    assert not provider_in_allowlist("bugbot")
    assert not provider_in_allowlist("human")


def test_author_allowlist_helpers() -> None:
    assert seat_from_author("chatgpt-codex-connector") == "codex"
    assert seat_from_author("copilot-pull-request-reviewer") == "copilot"
    assert seat_from_author("github-copilot[bot]") == "copilot"
    assert seat_from_author("ollama-artifact") == "ollama"
    assert seat_from_author("kas41") is None
    assert is_allowlisted_author("chatgpt-codex-connector")
    assert not is_allowlisted_author("random-user")
    assert "chatgpt-codex-connector" in REVIEWER_ALLOWLIST["codex"]


def test_dry_run_artifact_write(tmp_path: Path) -> None:
    path = write_review_artifact(
        pr=42,
        head_sha="abc123def456",
        model="kimi-k2.7-code:cloud",
        summary="scaffold dry-run review",
        dry_run=True,
        reviews_dir=tmp_path,
    )
    assert path == tmp_path / "pr-42.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["pr"] == 42
    assert payload["head_sha"] == "abc123def456"
    assert payload["model"] == "kimi-k2.7-code:cloud"
    assert payload["provider"] == "ollama"
    assert payload["summary"]
    assert payload["attestation"] == "dry-run"
    assert payload["dry_run"] is True
