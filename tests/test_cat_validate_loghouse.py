"""
Tests for scripts/cat_validate_loghouse.py

Covers all 7 public functions with both happy-path (real ROOT) and
failure-path (tmp_path) variants, targeting 15+ test cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cat_validate_loghouse import (
    check_schemas,
    check_modules,
    check_fixtures,
    check_normalize,
    check_engine_produces_findings,
    check_drift_report,
    write_report,
    LOGHOUSE_SCHEMAS,
    REQUIRED_FIXTURES,
    ENGINE_MODULES,
)
from scripts.common import ROOT


# ── check_schemas ──────────────────────────────────────────────────────────────

class TestCheckSchemas:
    def test_real_root_all_schemas_present(self):
        """All 7 LOGHOUSE schemas exist in the real repo — must return True."""
        ok, msgs = check_schemas(ROOT)
        assert ok is True
        assert len(msgs) == len(LOGHOUSE_SCHEMAS)
        assert all(msg.startswith("PASS") for msg in msgs)

    def test_missing_schemas_dir_returns_false(self, tmp_path):
        """A root with no schemas/ directory at all → False for every schema."""
        ok, msgs = check_schemas(tmp_path)
        assert ok is False
        assert len(msgs) == len(LOGHOUSE_SCHEMAS)
        assert all("FAIL schema missing" in msg for msg in msgs)

    def test_invalid_json_schema_returns_false(self, tmp_path):
        """A schema file that contains invalid JSON → False."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        # Place valid JSON stubs for all but the first schema
        first = LOGHOUSE_SCHEMAS[0]
        (schemas_dir / first).write_text("{ NOT VALID JSON !!!", encoding="utf-8")
        for name in LOGHOUSE_SCHEMAS[1:]:
            (schemas_dir / name).write_text('{"$schema": "https://json-schema.org/draft/2020-12/schema"}', encoding="utf-8")

        ok, msgs = check_schemas(tmp_path)
        assert ok is False
        fail_msgs = [m for m in msgs if "FAIL" in m]
        assert any(first in m for m in fail_msgs)

    def test_non_object_json_schema_returns_false(self, tmp_path):
        """A schema file whose JSON root is an array (not an object) → False."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        first = LOGHOUSE_SCHEMAS[0]
        (schemas_dir / first).write_text("[1, 2, 3]", encoding="utf-8")
        for name in LOGHOUSE_SCHEMAS[1:]:
            (schemas_dir / name).write_text('{"$schema": "x"}', encoding="utf-8")

        ok, msgs = check_schemas(tmp_path)
        assert ok is False
        assert any("FAIL" in m and first in m for m in msgs)

    def test_partial_schemas_present_returns_false(self, tmp_path):
        """Only some schemas present → False, with mixed PASS/FAIL messages."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        # Write only the first three
        for name in LOGHOUSE_SCHEMAS[:3]:
            (schemas_dir / name).write_text('{"$schema": "x"}', encoding="utf-8")

        ok, msgs = check_schemas(tmp_path)
        assert ok is False
        pass_count = sum(1 for m in msgs if m.startswith("PASS"))
        fail_count = sum(1 for m in msgs if m.startswith("FAIL"))
        assert pass_count == 3
        assert fail_count == len(LOGHOUSE_SCHEMAS) - 3


# ── check_modules ──────────────────────────────────────────────────────────────

class TestCheckModules:
    def test_all_engine_modules_import(self):
        """All 6 loghouse modules import without error — integration, no mocking."""
        ok, msgs = check_modules()
        assert ok is True
        assert len(msgs) == len(ENGINE_MODULES)
        assert all(msg.startswith("PASS") for msg in msgs)

    def test_returns_tuple_of_bool_and_list(self):
        """Return type is (bool, list[str])."""
        result = check_modules()
        assert isinstance(result, tuple) and len(result) == 2
        ok, msgs = result
        assert isinstance(ok, bool)
        assert isinstance(msgs, list)
        assert all(isinstance(m, str) for m in msgs)


# ── check_fixtures ─────────────────────────────────────────────────────────────

class TestCheckFixtures:
    def test_real_root_all_fixtures_present(self):
        """All required fixture files exist in the real repo → True."""
        ok, msgs = check_fixtures(ROOT)
        assert ok is True
        assert len(msgs) == len(REQUIRED_FIXTURES)
        assert all(msg.startswith("PASS") for msg in msgs)

    def test_missing_fixture_dir_returns_false(self, tmp_path):
        """A root with no fixture directory → False for every fixture."""
        ok, msgs = check_fixtures(tmp_path)
        assert ok is False
        assert len(msgs) == len(REQUIRED_FIXTURES)
        assert all("FAIL fixture missing" in msg for msg in msgs)

    def test_partial_fixtures_present_returns_false(self, tmp_path):
        """Only one fixture present → False, with one PASS and the rest FAIL."""
        fixture_dir = tmp_path / "tests" / "fixtures" / "loghouse"
        fixture_dir.mkdir(parents=True)
        first_rel = REQUIRED_FIXTURES[0]
        (tmp_path / first_rel).write_text("[]", encoding="utf-8")

        ok, msgs = check_fixtures(tmp_path)
        assert ok is False
        pass_count = sum(1 for m in msgs if m.startswith("PASS"))
        fail_count = sum(1 for m in msgs if m.startswith("FAIL"))
        assert pass_count == 1
        assert fail_count == len(REQUIRED_FIXTURES) - 1


# ── check_normalize ────────────────────────────────────────────────────────────

class TestCheckNormalize:
    def test_real_root_normalizes_successfully(self):
        """Real fixtures normalize cleanly and produce at least one envelope → True."""
        ok, msgs = check_normalize(ROOT)
        assert ok is True
        assert len(msgs) == 1
        assert msgs[0].startswith("PASS")
        assert "envelope" in msgs[0]

    def test_missing_raw_signals_returns_false(self, tmp_path):
        """Missing raw_signals.json → exception caught → False."""
        ok, msgs = check_normalize(tmp_path)
        assert ok is False
        assert len(msgs) == 1
        assert "FAIL" in msgs[0]

    def test_empty_raw_signals_returns_false(self, tmp_path):
        """raw_signals.json containing an empty list → 0 envelopes → False."""
        fixture_dir = tmp_path / "tests" / "fixtures" / "loghouse"
        fixture_dir.mkdir(parents=True)
        (fixture_dir / "raw_signals.json").write_text("[]", encoding="utf-8")

        ok, msgs = check_normalize(tmp_path)
        assert ok is False
        assert any("FAIL" in m for m in msgs)

    def test_malformed_raw_signals_returns_false(self, tmp_path):
        """raw_signals.json containing invalid JSON → exception caught → False."""
        fixture_dir = tmp_path / "tests" / "fixtures" / "loghouse"
        fixture_dir.mkdir(parents=True)
        (fixture_dir / "raw_signals.json").write_text("{ NOT JSON", encoding="utf-8")

        ok, msgs = check_normalize(tmp_path)
        assert ok is False
        assert any("FAIL" in m for m in msgs)


# ── check_engine_produces_findings ────────────────────────────────────────────

class TestCheckEngineProducesFindings:
    def test_real_root_produces_findings_and_dispatch(self):
        """Full engine pipeline with real fixtures → True, findings, dispatch items."""
        ok, msgs, findings, dispatch_items = check_engine_produces_findings(ROOT)
        assert ok is True, f"Engine check failed. Messages:\n" + "\n".join(msgs)
        assert len(findings) >= 1, "Expected at least one finding"
        assert len(dispatch_items) >= 1, "Expected at least one dispatch item"
        # All findings must carry evidence
        for f in findings:
            assert f.get("evidence"), f"Finding {f.get('finding_id')} has no evidence"

    def test_returns_four_tuple(self):
        """Return type is (bool, list[str], list[dict], list[dict])."""
        result = check_engine_produces_findings(ROOT)
        assert isinstance(result, tuple) and len(result) == 4
        ok, msgs, findings, dispatch_items = result
        assert isinstance(ok, bool)
        assert isinstance(msgs, list)
        assert isinstance(findings, list)
        assert isinstance(dispatch_items, list)

    def test_missing_fixtures_returns_false(self, tmp_path):
        """A root with no fixtures → exception caught → False, empty lists."""
        ok, msgs, findings, dispatch_items = check_engine_produces_findings(tmp_path)
        assert ok is False
        assert any("FAIL" in m for m in msgs)
        assert findings == []
        assert dispatch_items == []


# ── check_drift_report ────────────────────────────────────────────────────────

class TestCheckDriftReport:
    def test_real_root_drift_report_valid(self):
        """Real architecture_rules.yaml + real fixtures → report validates → True."""
        ok, msgs = check_drift_report(ROOT)
        assert ok is True, f"Drift check failed. Messages:\n" + "\n".join(msgs)
        assert any("PASS" in m for m in msgs)

    def test_missing_architecture_rules_returns_false(self, tmp_path):
        """No architecture_rules.yaml at expected path → returns False immediately."""
        ok, msgs = check_drift_report(tmp_path)
        assert ok is False
        assert len(msgs) >= 1
        assert any("FAIL drift rules missing" in m for m in msgs)

    def test_returns_tuple_of_bool_and_list(self):
        """Return type is (bool, list[str])."""
        result = check_drift_report(ROOT)
        assert isinstance(result, tuple) and len(result) == 2
        ok, msgs = result
        assert isinstance(ok, bool)
        assert isinstance(msgs, list)


# ── write_report ───────────────────────────────────────────────────────────────

class TestWriteReport:
    def _sample_results(self) -> list[dict]:
        return [
            {"check": "schemas", "ok": True, "details": ["PASS schema exists: foo.schema.json"]},
            {"check": "fixtures", "ok": True, "details": ["PASS fixture exists: tests/fixtures/loghouse/raw_signals.json"]},
        ]

    def test_write_report_creates_file_with_pass(self, tmp_path):
        """overall_ok=True → file created, JSON valid, overall field is PASS."""
        report_path = write_report(tmp_path, self._sample_results(), overall_ok=True)
        assert report_path.exists(), "Report file was not created"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["overall"] == "PASS"
        assert data["mission_id"] == "MP-CAT-A007-4C01"
        assert data["validator"] == "cat_validate_loghouse.py"
        assert "generated_at" in data
        assert data["checks"] == self._sample_results()

    def test_write_report_creates_file_with_fail(self, tmp_path):
        """overall_ok=False → overall field is FAIL."""
        results = [{"check": "schemas", "ok": False, "details": ["FAIL schema missing: foo.schema.json"]}]
        report_path = write_report(tmp_path, results, overall_ok=False)
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["overall"] == "FAIL"

    def test_write_report_creates_parent_dirs(self, tmp_path):
        """write_report creates evidence/reports/ if it does not exist."""
        report_path = write_report(tmp_path, [], overall_ok=True)
        expected_dir = tmp_path / "evidence" / "reports"
        assert expected_dir.is_dir()
        assert report_path.parent == expected_dir

    def test_write_report_returns_path(self, tmp_path):
        """Return value is a Path pointing at the created file."""
        result = write_report(tmp_path, [], overall_ok=True)
        assert isinstance(result, Path)
        assert result.name == "MP-CAT-A007-4C01_validation_report.json"

    def test_write_report_empty_checks_list(self, tmp_path):
        """Empty results list → checks field is [] in the JSON output."""
        report_path = write_report(tmp_path, [], overall_ok=True)
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["checks"] == []

    def test_write_report_overwrites_on_second_call(self, tmp_path):
        """Calling write_report twice overwrites the previous report."""
        write_report(tmp_path, self._sample_results(), overall_ok=True)
        report_path = write_report(tmp_path, [], overall_ok=False)
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["overall"] == "FAIL"
        assert data["checks"] == []
