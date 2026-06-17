"""
tests/test_cat_stats.py

Deterministic but tolerant assertions against real repo data.
The worker generates scripts/cat_stats.py; these tests verify its contract.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Allow importing from scripts/ without installing the package
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Import under test — deferred so missing file produces a clear error
# ---------------------------------------------------------------------------
cat_stats = pytest.importorskip(
    "cat_stats",
    reason="scripts/cat_stats.py not yet created by worker",
)


# ---------------------------------------------------------------------------
# summarize() contract
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_returns_dict(self):
        result = cat_stats.summarize()
        assert isinstance(result, dict), "summarize() must return a dict"

    def test_required_keys(self):
        result = cat_stats.summarize()
        required_keys = {
            "total_missions",
            "missions_by_status",
            "active_mission_id",
            "total_active_beads",
            "beads_by_status",
        }
        missing = required_keys - result.keys()
        assert not missing, f"summarize() result missing keys: {missing}"

    def test_total_missions_minimum(self):
        result = cat_stats.summarize()
        assert result["total_missions"] >= 3, (
            f"Expected at least 3 missions, got {result['total_missions']}"
        )

    def test_missions_by_status_is_dict(self):
        result = cat_stats.summarize()
        assert isinstance(result["missions_by_status"], dict), (
            "missions_by_status must be a dict"
        )

    def test_missions_by_status_has_approved(self):
        result = cat_stats.summarize()
        mbs = result["missions_by_status"]
        assert "approved" in mbs, (
            f"'approved' must be a key in missions_by_status; got keys: {list(mbs.keys())}"
        )

    def test_active_mission_id(self):
        # active_mission_id is lifecycle-dependent: null between sprints, or an
        # MP-* id while a mission is active. Assert shape, not a specific value.
        result = cat_stats.summarize()
        amid = result["active_mission_id"]
        assert amid is None or (isinstance(amid, str) and amid.startswith("MP-")), (
            f"active_mission_id must be null or an MP-* id, got {amid!r}"
        )

    def test_total_active_beads_minimum(self):
        result = cat_stats.summarize()
        assert result["total_active_beads"] >= 4, (
            f"Expected at least 4 active beads, got {result['total_active_beads']}"
        )

    def test_beads_by_status_is_dict(self):
        result = cat_stats.summarize()
        assert isinstance(result["beads_by_status"], dict), (
            "beads_by_status must be a dict"
        )

    def test_beads_by_status_sum_equals_total(self):
        result = cat_stats.summarize()
        status_sum = sum(result["beads_by_status"].values())
        assert status_sum == result["total_active_beads"], (
            f"Sum of beads_by_status values ({status_sum}) must equal "
            f"total_active_beads ({result['total_active_beads']})"
        )

    def test_missions_by_status_sums_to_total(self):
        """Every mission is counted under exactly one status (lifecycle-agnostic)."""
        result = cat_stats.summarize()
        status_sum = sum(result["missions_by_status"].values())
        assert status_sum == result["total_missions"], (
            f"missions_by_status sum ({status_sum}) must equal "
            f"total_missions ({result['total_missions']})"
        )


# ---------------------------------------------------------------------------
# --json CLI output
# ---------------------------------------------------------------------------

class TestJsonCli:
    def test_json_flag_produces_valid_json(self):
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "scripts/cat_stats.py", "--json"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"cat_stats.py --json exited with code {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(f"--json output is not valid JSON: {exc}\nOutput: {result.stdout[:500]}")

        required_keys = {
            "total_missions",
            "missions_by_status",
            "active_mission_id",
            "total_active_beads",
            "beads_by_status",
        }
        missing = required_keys - data.keys()
        assert not missing, f"JSON output missing keys: {missing}"

    def test_default_output_is_human_readable(self):
        """Without --json, output should be non-empty text (not necessarily valid JSON)."""
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "scripts/cat_stats.py"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"cat_stats.py exited with code {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )
        assert result.stdout.strip(), "Default output must not be empty"
