"""Tests for cat_adapter_config and cat_adapter_state JSON schemas."""
import json
from pathlib import Path
import pytest
import jsonschema
from jsonschema import validate, ValidationError

ROOT = Path(__file__).parent.parent
CONFIG_SCHEMA = ROOT / 'schemas' / 'cat_adapter_config.schema.json'
STATE_SCHEMA = ROOT / 'schemas' / 'cat_adapter_state.schema.json'
FIXTURES = ROOT / 'tests' / 'fixtures' / 'adapter'


def load_json(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Config schema
# ---------------------------------------------------------------------------

class TestAdapterConfigSchema:
    def test_valid_config_fixture_passes(self):
        schema = load_json(CONFIG_SCHEMA)
        instance = load_json(FIXTURES / 'valid_config.json')
        validate(instance=instance, schema=schema)

    def test_minimal_config_passes(self):
        schema = load_json(CONFIG_SCHEMA)
        validate(instance={
            "adapter_version": "1.0",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "repo_name": "my-project",
            "sync_mode": "read_only",
        }, schema=schema)

    def test_missing_required_field_fails(self):
        schema = load_json(CONFIG_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
                # sync_mode missing
            }, schema=schema)

    def test_invalid_sync_mode_fails(self):
        schema = load_json(CONFIG_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
                "sync_mode": "automatic",  # not in enum
            }, schema=schema)

    def test_no_additional_properties(self):
        schema = load_json(CONFIG_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "repo_name": "my-project",
                "sync_mode": "read_only",
                "db_connection_string": "postgres://...",  # rejected
            }, schema=schema)

    def test_invalid_mission_id_pattern_fails(self):
        schema = load_json(CONFIG_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "adapter_version": "1.0",
                "cat_mission_id": "INVALID-ID",
                "repo_name": "my-project",
                "sync_mode": "read_only",
            }, schema=schema)

    def test_manual_sync_mode_passes(self):
        schema = load_json(CONFIG_SCHEMA)
        validate(instance={
            "adapter_version": "1.0",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "repo_name": "my-project",
            "sync_mode": "manual",
        }, schema=schema)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class TestAdapterStateSchema:
    def test_valid_state_fixture_passes(self):
        schema = load_json(STATE_SCHEMA)
        instance = load_json(FIXTURES / 'valid_state.json')
        validate(instance=instance, schema=schema)

    def test_minimal_state_passes(self):
        schema = load_json(STATE_SCHEMA)
        validate(instance={
            "snapshot_timestamp": "2026-06-18T14:00:00Z",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "mission_status": "in_progress",
            "active_bead_id": None,
            "last_sync": None,
        }, schema=schema)

    def test_missing_required_field_fails(self):
        schema = load_json(STATE_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
                # active_bead_id and last_sync missing
            }, schema=schema)

    def test_invalid_mission_status_fails(self):
        schema = load_json(STATE_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "running",  # not in enum
                "active_bead_id": None,
                "last_sync": None,
            }, schema=schema)

    def test_no_additional_properties(self):
        schema = load_json(STATE_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
                "active_bead_id": None,
                "last_sync": None,
                "secret_token": "abc123",  # rejected
            }, schema=schema)

    def test_bead_statuses_optional(self):
        schema = load_json(STATE_SCHEMA)
        validate(instance={
            "snapshot_timestamp": "2026-06-18T14:00:00Z",
            "cat_mission_id": "MP-CAT-A012-4C01",
            "mission_status": "approved",
            "active_bead_id": None,
            "last_sync": None,
            # bead_statuses omitted — should pass
        }, schema=schema)

    def test_invalid_bead_status_value_fails(self):
        schema = load_json(STATE_SCHEMA)
        with pytest.raises(ValidationError):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": "in_progress",
                "active_bead_id": None,
                "last_sync": None,
                "bead_statuses": {
                    "BEAD-CAT-A012-4C01-01": "pending",  # not in enum
                },
            }, schema=schema)

    def test_all_terminal_mission_statuses_valid(self):
        schema = load_json(STATE_SCHEMA)
        for status in ("completed", "closed", "learned", "abandoned"):
            validate(instance={
                "snapshot_timestamp": "2026-06-18T14:00:00Z",
                "cat_mission_id": "MP-CAT-A012-4C01",
                "mission_status": status,
                "active_bead_id": None,
                "last_sync": None,
            }, schema=schema)
