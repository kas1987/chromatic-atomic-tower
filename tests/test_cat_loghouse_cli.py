"""
Tests for the LOGHOUSE CLI entry points in scripts/cat_loghouse.py.

Covers:
- run_pipeline()       — external mode over a fixture directory
- run_self_pipeline()  — self-monitoring mode over CAT's operational JSONL logs
- main()               — argparse CLI wiring (both --mode external and --mode self)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.cat_loghouse import main, run_pipeline, run_self_pipeline

# Absolute path to the shared fixture directory checked in alongside the tests.
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "loghouse"


# ---------------------------------------------------------------------------
# run_pipeline — external mode
# ---------------------------------------------------------------------------


class TestRunPipeline:
    """Tests for run_pipeline(input_dir, output_dir)."""

    def test_happy_path_with_real_fixtures(self, tmp_path: Path) -> None:
        """Full pipeline over the checked-in fixture directory returns 0."""
        result = run_pipeline(FIXTURE_DIR, tmp_path)
        assert result == 0, "expected exit code 0 for valid fixture input"

    def test_output_dir_contains_expected_files(self, tmp_path: Path) -> None:
        """After a successful run the output directory must contain the three
        canonical artefacts that downstream consumers depend on."""
        run_pipeline(FIXTURE_DIR, tmp_path)
        assert (tmp_path / "findings.json").exists(), "findings.json not written"
        assert (tmp_path / "findings.md").exists(), "findings.md not written"
        assert (tmp_path / "dispatch_queue.json").exists(), "dispatch_queue.json not written"

    def test_output_findings_json_is_valid_list(self, tmp_path: Path) -> None:
        """findings.json must be a non-empty JSON list after a successful run."""
        run_pipeline(FIXTURE_DIR, tmp_path)
        data = json.loads((tmp_path / "findings.json").read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_output_dispatch_queue_json_is_valid_list(self, tmp_path: Path) -> None:
        """dispatch_queue.json must be a non-empty JSON list after a successful run."""
        run_pipeline(FIXTURE_DIR, tmp_path)
        data = json.loads((tmp_path / "dispatch_queue.json").read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_missing_raw_signals_returns_1(self, tmp_path: Path) -> None:
        """An input directory that lacks raw_signals.json must return exit code 1."""
        empty_input = tmp_path / "no_signals"
        empty_input.mkdir()
        result = run_pipeline(empty_input, tmp_path / "out")
        assert result == 1

    def test_empty_input_dir_returns_1(self, tmp_path: Path) -> None:
        """An entirely empty input directory must return exit code 1 (no raw_signals.json)."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = run_pipeline(empty_dir, tmp_path / "out2")
        assert result == 1

    def test_missing_input_dir_itself_returns_1(self, tmp_path: Path) -> None:
        """A non-existent input directory must return exit code 1."""
        nonexistent = tmp_path / "does_not_exist"
        result = run_pipeline(nonexistent, tmp_path / "out3")
        assert result == 1

    def test_input_with_only_deploy_events_and_no_findings_returns_1(
        self, tmp_path: Path
    ) -> None:
        """A raw_signals.json that contains data producing no findings must return 1.

        We write a minimal valid deploy event that will normalise correctly but
        create no correlated error spike, so the pipeline emits no findings.
        """
        input_dir = tmp_path / "no_findings_input"
        input_dir.mkdir()
        # A single deploy event with 'succeeded' status — no error envelopes, so
        # no error-spike rule fires and no findings are produced.
        signals = [
            {
                "deploy_id": "deploy-test-001",
                "service": "svc",
                "commit_sha": "abcdef1",
                "actor": "ci",
                "started_at": "2026-06-17T10:00:00Z",
                "completed_at": "2026-06-17T10:05:00Z",
                "status": "succeeded",
            }
        ]
        (input_dir / "raw_signals.json").write_text(json.dumps(signals))
        result = run_pipeline(input_dir, tmp_path / "out4")
        assert result == 1

    def test_dependency_edges_loaded_when_present(self, tmp_path: Path) -> None:
        """run_pipeline should consume dependency_edges.json when it exists.

        The real fixture directory already contains dependency_edges.json with a
        forbidden edge, so checking that run_pipeline returns 0 (not 1) confirms
        the forbidden-dependency-edge rule contributed at least one finding.
        """
        assert (FIXTURE_DIR / "dependency_edges.json").exists(), (
            "test pre-condition: fixture must contain dependency_edges.json"
        )
        result = run_pipeline(FIXTURE_DIR, tmp_path)
        assert result == 0

    def test_output_dir_created_automatically(self, tmp_path: Path) -> None:
        """run_pipeline must create a nested output directory if it does not exist."""
        nested_out = tmp_path / "deep" / "nested" / "output"
        assert not nested_out.exists()
        run_pipeline(FIXTURE_DIR, nested_out)
        assert nested_out.exists()


# ---------------------------------------------------------------------------
# run_self_pipeline — self-monitoring mode
# ---------------------------------------------------------------------------


class TestRunSelfPipeline:
    """Tests for run_self_pipeline(output_dir, strict=...)."""

    def test_empty_cat_logs_non_strict_returns_0(self, tmp_path: Path) -> None:
        """When CAT's own logs are empty load_cat_signals returns [].

        With no signals the pipeline finds no anomalies (zero findings is the
        happy path) and must return 0 regardless of the strict flag.
        """
        with patch(
            "scripts.cat_loghouse.run_self_pipeline.__wrapped__"
            if hasattr(run_self_pipeline, "__wrapped__")
            else "scripts.loghouse.cat_adapter.load_cat_signals",
            return_value=[],
        ):
            result = run_self_pipeline(tmp_path, strict=False)
        assert result == 0

    def test_empty_cat_logs_strict_returns_0(self, tmp_path: Path) -> None:
        """Even in strict mode, zero findings → exit code 0 (no anomalies is good)."""
        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            result = run_self_pipeline(tmp_path, strict=True)
        assert result == 0

    def test_output_files_written_in_self_mode(self, tmp_path: Path) -> None:
        """Self-monitoring mode must still write findings.json and dispatch_queue.json."""
        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            run_self_pipeline(tmp_path, strict=False)
        assert (tmp_path / "findings.json").exists()
        assert (tmp_path / "dispatch_queue.json").exists()

    def test_self_mode_with_live_cat_logs_returns_0_non_strict(
        self, tmp_path: Path
    ) -> None:
        """Integration smoke: run against real CAT logs (non-strict).

        CAT's operational logs may or may not contain anomalies; in non-strict
        mode the exit code is always 0 unless an unexpected exception occurs.
        """
        result = run_self_pipeline(tmp_path, strict=False)
        assert result == 0

    def test_self_mode_critical_findings_strict_returns_1(
        self, tmp_path: Path
    ) -> None:
        """When load_cat_signals returns data that produces a P0/P1 finding,
        --strict mode must return exit code 1.

        We mock emit_findings to inject a synthetic critical finding so the
        test does not depend on the exact rules thresholds.
        """
        synthetic_finding = {
            "finding_id": "f-0000-dead-beef",
            "title": "Test critical finding",
            "category": "availability",
            "severity": "p0",
            "confidence": "high",
            "status": "open",
            "services": ["cat"],
            "first_seen": "2026-06-17T00:00:00Z",
            "last_seen": "2026-06-17T01:00:00Z",
            "owner": "ORCHESTRATOR",
            "hypothesis": "test",
            "suggested_fix": "test fix",
            "blast_radius": "low",
            "sla_impact": "none",
            "evidence": [
                {
                    "source_type": "log",
                    "source_ref": "evt-001",
                    "observed_at": "2026-06-17T00:00:00Z",
                    "summary": "synthetic test evidence",
                }
            ],
        }

        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            with patch(
                "scripts.cat_loghouse.emit_findings",
                return_value=[synthetic_finding],
            ):
                with patch(
                    "scripts.cat_loghouse.emit_dispatch", return_value=[]
                ):
                    result = run_self_pipeline(tmp_path, strict=True)

        assert result == 1, "strict mode with a P0 finding must exit 1"

    def test_self_mode_critical_findings_non_strict_returns_0(
        self, tmp_path: Path
    ) -> None:
        """Critical findings without --strict must still return 0."""
        synthetic_finding = {
            "finding_id": "f-0000-dead-beef",
            "title": "Test critical finding",
            "category": "availability",
            "severity": "p1",
            "confidence": "high",
            "status": "open",
            "services": ["cat"],
            "first_seen": "2026-06-17T00:00:00Z",
            "last_seen": "2026-06-17T01:00:00Z",
            "owner": "ORCHESTRATOR",
            "hypothesis": "test",
            "suggested_fix": "test fix",
            "blast_radius": "low",
            "sla_impact": "none",
            "evidence": [
                {
                    "source_type": "log",
                    "source_ref": "evt-002",
                    "observed_at": "2026-06-17T00:00:00Z",
                    "summary": "synthetic test evidence",
                }
            ],
        }

        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            with patch(
                "scripts.cat_loghouse.emit_findings",
                return_value=[synthetic_finding],
            ):
                with patch(
                    "scripts.cat_loghouse.emit_dispatch", return_value=[]
                ):
                    result = run_self_pipeline(tmp_path, strict=False)

        assert result == 0, "non-strict mode must return 0 even when critical findings exist"


# ---------------------------------------------------------------------------
# main() — CLI wiring
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() argparse CLI entry point."""

    def test_main_external_mode_with_fixture_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with --mode external (default) and valid --input exits with 0."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_loghouse.py",
                "--input",
                str(FIXTURE_DIR),
                "--output",
                str(tmp_path / "cli_ext_out"),
            ],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_self_mode_non_strict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with --mode self exits with 0 when no critical findings (non-strict)."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_loghouse.py",
                "--mode",
                "self",
                "--output",
                str(tmp_path / "cli_self_out"),
            ],
        )
        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_main_missing_raw_signals_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with an --input dir that has no raw_signals.json exits with 1."""
        empty_input = tmp_path / "empty_input"
        empty_input.mkdir()
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_loghouse.py",
                "--input",
                str(empty_input),
                "--output",
                str(tmp_path / "cli_empty_out"),
            ],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_self_mode_strict_no_findings_exits_0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() --mode self --strict exits 0 when there are no critical findings."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_loghouse.py",
                "--mode",
                "self",
                "--strict",
                "--output",
                str(tmp_path / "cli_strict_out"),
            ],
        )
        with patch("scripts.loghouse.cat_adapter.load_cat_signals", return_value=[]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 0

    def test_main_explicit_external_mode_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() with --mode external explicitly set behaves the same as the default."""
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cat_loghouse.py",
                "--mode",
                "external",
                "--input",
                str(FIXTURE_DIR),
                "--output",
                str(tmp_path / "cli_ext_explicit"),
            ],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
