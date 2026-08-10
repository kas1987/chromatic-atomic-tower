"""Tests for the A012 adapter schemas and the A020 portable boundary."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate


ROOT = Path(__file__).parent.parent
LEGACY_CONFIG_SCHEMA = ROOT / "schemas" / "cat_adapter_config.schema.json"
LEGACY_STATE_SCHEMA = ROOT / "schemas" / "cat_adapter_state.schema.json"
CONFIG_SCHEMA_PATH = ROOT / "schemas" / "adapter_config.schema.json"
STATE_SCHEMA_PATH = ROOT / "schemas" / "adapter_state.schema.json"
FIXTURES = ROOT / "tests" / "fixtures" / "adapter"


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# A012 adapter schema coverage remains intact.
class TestLegacyAdapterConfigSchema:
    def test_valid_config_fixture_passes(self):
        validate(instance=load_json(FIXTURES / "valid_config.json"), schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_minimal_config_passes(self):
        validate(instance={
            "adapter_version": "1.0",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "repo_name": "my-project",
            "sync_mode": "read_only",
        }, schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_missing_required_field_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
            }, schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_invalid_sync_mode_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
                "sync_mode": "automatic",
            }, schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_no_additional_properties(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
                "sync_mode": "read_only",
                "db_connection_string": "postgres://...",
            }, schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_invalid_mission_id_pattern_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "INVALID-ID",
                "repo_name": "my-project",
                "sync_mode": "read_only",
            }, schema=load_json(LEGACY_CONFIG_SCHEMA))

    def test_manual_sync_mode_passes(self):
        validate(instance={
            "adapter_version": "1.0",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "repo_name": "my-project",
            "sync_mode": "manual",
        }, schema=load_json(LEGACY_CONFIG_SCHEMA))


class TestLegacyAdapterStateSchema:
    def test_valid_state_fixture_passes(self):
        validate(instance=load_json(FIXTURES / "valid_state.json"), schema=load_json(LEGACY_STATE_SCHEMA))

    def test_minimal_state_passes(self):
        validate(instance={
            "snapshot_timestamp": "2026-06-18T14:00:00Z",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "mission_status": "in_progress",
            "active_bead_id": None,
            "last_sync": None,
        }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_missing_required_field_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
            }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_invalid_mission_status_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "running",
                "active_bead_id": None,
                "last_sync": None,
            }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_no_additional_properties(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
                "active_bead_id": None,
                "last_sync": None,
                "secret_token": "abc123",
            }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_bead_statuses_optional(self):
        validate(instance={
            "snapshot_timestamp": "2026-06-18T14:00:00Z",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "mission_status": "approved",
            "active_bead_id": None,
            "last_sync": None,
        }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_invalid_bead_status_value_fails(self):
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
                "active_bead_id": None,
                "last_sync": None,
                "bead_statuses": {"BEAD-CAT-A012-4C01-01": "pending"},
            }, schema=load_json(LEGACY_STATE_SCHEMA))

    def test_all_terminal_mission_statuses_valid(self):
        for status in ("completed", "closed", "learned", "abandoned"):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": status,
                "active_bead_id": None,
                "last_sync": None,
            }, schema=load_json(LEGACY_STATE_SCHEMA))


def valid_config() -> dict:
    return {
        "contract_version": "1.0.0",
        "cat_mission_id": "MP-CAT-A020-4C01",
        "consumer_repo": "harness-v2",
        "execution_mode": "evidence_only",
        "cat_authority": {
            "read_paths": ["missions/registry/MISSION_REGISTRY.yaml"],
            "write_paths": [],
        },
        "consumer_authority": {
            "read_paths": [".cat/config.json"],
            "write_paths": ["evidence/runtime.json"],
        },
    }


def valid_state() -> dict:
    return {
        "contract_version": "1.0.0",
        "cat_mission_id": "MP-CAT-A020-4C01",
        "consumer_repo": "harness-v2",
        "observed_at": "2026-08-08T14:00:00Z",
        "execution_status": "succeeded",
        "active_bead_id": "BEAD-CAT-A020-4C01-02",
        "cat_authority": {"write_paths": []},
        "evidence": {
            "path": "evidence/runtime.json",
            "validation_command": "python -m pytest tests/test_runtime.py -q",
            "validation_result": "pass",
        },
    }


class TestA020PortableAdapterContract:
    def test_schemas_are_valid_draft_2020_12_schemas(self):
        Draft202012Validator.check_schema(load_json(CONFIG_SCHEMA_PATH))
        Draft202012Validator.check_schema(load_json(STATE_SCHEMA_PATH))

    def test_versioned_config_accepts_evidence_only_consumer(self):
        validate(instance=valid_config(), schema=load_json(CONFIG_SCHEMA_PATH))

    def test_config_rejects_cat_write_authority(self):
        instance = valid_config()
        instance["cat_authority"]["write_paths"] = ["missions/registry/MISSION_REGISTRY.yaml"]
        with pytest.raises(ValidationError):
            validate(instance=instance, schema=load_json(CONFIG_SCHEMA_PATH))

    def test_config_rejects_unknown_contract_version(self):
        instance = valid_config()
        instance["contract_version"] = "2.0.0"
        with pytest.raises(ValidationError):
            validate(instance=instance, schema=load_json(CONFIG_SCHEMA_PATH))

    def test_config_rejects_absolute_or_traversal_paths(self):
        for path in ("/outside/repo", "../outside", "C:/outside"):
            instance = valid_config()
            instance["consumer_authority"]["write_paths"] = [path]
            with pytest.raises(ValidationError):
                validate(instance=instance, schema=load_json(CONFIG_SCHEMA_PATH))

    def test_state_requires_traceable_execution_evidence(self):
        validate(instance=valid_state(), schema=load_json(STATE_SCHEMA_PATH))
        missing_command = valid_state()
        del missing_command["evidence"]["validation_command"]
        with pytest.raises(ValidationError):
            validate(instance=missing_command, schema=load_json(STATE_SCHEMA_PATH))

    def test_state_rejects_cat_write_authority_and_unknown_version(self):
        instance = valid_state()
        instance["cat_authority"]["write_paths"] = ["state/TOWER_STATE.yaml"]
        with pytest.raises(ValidationError):
            validate(instance=instance, schema=load_json(STATE_SCHEMA_PATH))

        instance = valid_state()
        instance["contract_version"] = "1.1.0"
        with pytest.raises(ValidationError):
            validate(instance=instance, schema=load_json(STATE_SCHEMA_PATH))
