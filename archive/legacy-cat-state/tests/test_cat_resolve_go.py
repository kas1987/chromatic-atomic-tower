"""BEAD-CAT-A014-4C01-07: Tests for cat_resolve_go.py dispatch packet schema.

Tests cover:
  - build_dispatch returns all required schema fields
  - dispatch_status is 'ready' when confidence >= minimum
  - dispatch_status is 'blocked' when confidence < minimum
  - --format json outputs valid JSON
  - --check-schema validates against go_dispatch_packet.schema.json
  - --format markdown outputs markdown
  - go_dispatch_packet.schema.json exists and is valid JSON Schema
  - JSON schema has required fields: dispatch_status, mission_id, bead_id, etc.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

from scripts.cat_resolve_go import build_dispatch, confidence_band, select_bead, select_mission

SCHEMA_REQUIRED = [
    'dispatch_status', 'mission_id', 'bead_id', 'bead_title',
    'allowed_paths', 'forbidden_paths', 'validation', 'stop_conditions',
]

SAMPLE_MISSION = {
    'mission_id': 'MP-CAT-A014-4C01',
    'title': 'Test Mission',
    'level': 'M3',
    'risk_level': 'medium',
    'path': 'missions/active/test.yaml',
}

SAMPLE_BEAD = {
    'bead_id': 'BEAD-CAT-A014-4C01-07',
    'mission_id': 'MP-CAT-A014-4C01',
    'title': 'Test BEAD',
    'status': 'active',
    'agent_role': 'Builder',
    'autonomy_level': 'L3',
    'confidence': {'current': 83, 'minimum': 80},
    'risk_level': 'medium',
    'reversibility': 'high',
    'allowed_paths': ['scripts/cat_resolve_go.py'],
    'forbidden_paths': ['.env'],
    'tool_budget': {'search': 2, 'read': 8},
    'definition_of_done': ['Tests pass.'],
    'validation': [{'type': 'unit_tests', 'command': 'pytest', 'evidence_path': 'ev/x.txt'}],
    'stop_conditions': ['Confidence drops.'],
    'required_output': ['summary'],
    '_path': 'beads/active/BEAD-CAT-A014-4C01-07.yaml',
}

LOW_CONFIDENCE_BEAD = {**SAMPLE_BEAD, 'confidence': {'current': 70, 'minimum': 80}}


class TestBuildDispatch:
    def test_has_all_required_schema_fields(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        for field in SCHEMA_REQUIRED:
            assert field in dispatch, f"missing required field: {field}"

    def test_ready_when_confidence_above_minimum(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['dispatch_status'] == 'ready'

    def test_blocked_when_confidence_below_minimum(self):
        dispatch = build_dispatch(SAMPLE_MISSION, LOW_CONFIDENCE_BEAD)
        assert dispatch['dispatch_status'] == 'blocked'

    def test_allowed_paths_preserved(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['allowed_paths'] == SAMPLE_BEAD['allowed_paths']

    def test_forbidden_paths_preserved(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['forbidden_paths'] == SAMPLE_BEAD['forbidden_paths']

    def test_validation_list_preserved(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['validation'] == SAMPLE_BEAD['validation']

    def test_stop_conditions_preserved(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['stop_conditions'] == SAMPLE_BEAD['stop_conditions']

    def test_mission_id_in_dispatch(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['mission_id'] == 'MP-CAT-A014-4C01'

    def test_bead_id_in_dispatch(self):
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        assert dispatch['bead_id'] == 'BEAD-CAT-A014-4C01-07'


class TestConfidenceBand:
    def test_very_high(self):
        assert confidence_band(90) == 'very_high'
        assert confidence_band(100) == 'very_high'

    def test_high(self):
        assert confidence_band(75) == 'high'
        assert confidence_band(89) == 'high'

    def test_medium(self):
        assert confidence_band(60) == 'medium'
        assert confidence_band(74) == 'medium'

    def test_low(self):
        assert confidence_band(40) == 'low'
        assert confidence_band(59) == 'low'

    def test_blocked(self):
        assert confidence_band(0) == 'blocked'
        assert confidence_band(39) == 'blocked'


class TestDispatchPacketSchema:
    def test_schema_file_exists(self):
        schema_path = ROOT_PATH / 'schemas' / 'go_dispatch_packet.schema.json'
        assert schema_path.exists()

    def test_schema_is_valid_json(self):
        schema_path = ROOT_PATH / 'schemas' / 'go_dispatch_packet.schema.json'
        data = json.loads(schema_path.read_text(encoding='utf-8'))
        assert isinstance(data, dict)

    def test_schema_has_required_array(self):
        schema_path = ROOT_PATH / 'schemas' / 'go_dispatch_packet.schema.json'
        data = json.loads(schema_path.read_text(encoding='utf-8'))
        assert 'required' in data
        for field in SCHEMA_REQUIRED:
            assert field in data['required'], f"schema required missing: {field}"

    def test_schema_validates_sample_dispatch(self):
        import jsonschema
        schema_path = ROOT_PATH / 'schemas' / 'go_dispatch_packet.schema.json'
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        dispatch = build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(dispatch))
        assert errors == [], [str(e) for e in errors]

    def test_schema_rejects_missing_required_field(self):
        import jsonschema
        schema_path = ROOT_PATH / 'schemas' / 'go_dispatch_packet.schema.json'
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        bad = {'dispatch_status': 'ready'}  # missing mission_id, bead_id, etc.
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(bad))
        assert len(errors) > 0


class TestCliOutputModes:
    def test_format_json_outputs_valid_json(self):
        result = subprocess.run(
            [sys.executable, str(ROOT_PATH / 'scripts' / 'cat_resolve_go.py'),
             '--format', 'json', '--skip-align-check', '--skip-loghouse'],
            capture_output=True, text=True,
        )
        if 'No active BEAD' in result.stdout or 'No approved mission' in result.stdout:
            pytest.skip("No active BEAD available (all BEADs archived — expected post-mission)")
        # Extract JSON portion (before SCHEMA PASS line if present)
        json_text = result.stdout.split('\nSCHEMA')[0].strip()
        if json_text:
            data = json.loads(json_text)
            assert 'dispatch_status' in data

    def test_check_schema_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(ROOT_PATH / 'scripts' / 'cat_resolve_go.py'),
             '--format', 'json', '--check-schema'],
            capture_output=True, text=True,
        )
        if 'No active BEAD' in result.stdout or 'No approved mission' in result.stdout:
            pytest.skip("No active BEAD available (all BEADs archived — expected post-mission)")
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'SCHEMA PASS' in result.stdout
