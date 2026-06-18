"""Tests for cat_adapter_init.py — adapter scaffold generator."""
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import cat_adapter_init as init_mod


# ---------------------------------------------------------------------------
# Unit tests for pure helpers
# ---------------------------------------------------------------------------

class TestBuildConfig:
    def test_required_fields_present(self):
        cfg = init_mod.build_config('MP-CAT-A012-4C01', 'my-repo', 'read_only')
        assert cfg['adapter_version'] == '1.0'
        assert cfg['cat_mission_id'] == 'MP-CAT-A012-4C01'
        assert cfg['repo_name'] == 'my-repo'
        assert cfg['sync_mode'] == 'read_only'

    def test_manual_sync_mode(self):
        cfg = init_mod.build_config('MP-CAT-A012-4C01', 'r', 'manual')
        assert cfg['sync_mode'] == 'manual'

    def test_config_validates_against_schema(self):
        import jsonschema
        cfg = init_mod.build_config('MP-CAT-A012-4C01', 'my-repo', 'read_only')
        schema = json.loads(init_mod.CONFIG_SCHEMA_PATH.read_text())
        jsonschema.validate(instance=cfg, schema=schema)

    def test_no_extra_fields(self):
        cfg = init_mod.build_config('MP-CAT-A012-4C01', 'r', 'read_only')
        allowed = {'adapter_version', 'cat_mission_id', 'repo_name', 'sync_mode'}
        assert set(cfg.keys()) == allowed


class TestBuildState:
    def test_required_fields_present(self):
        state = init_mod.build_state('MP-CAT-A012-4C01')
        assert state['cat_mission_id'] == 'MP-CAT-A012-4C01'
        assert 'snapshot_timestamp' in state
        assert 'mission_status' in state
        assert 'active_bead_id' in state
        assert 'last_sync' in state

    def test_state_validates_against_schema(self):
        import jsonschema
        state = init_mod.build_state('MP-CAT-A012-4C01')
        schema = json.loads(init_mod.STATE_SCHEMA_PATH.read_text())
        jsonschema.validate(instance=state, schema=schema)


# ---------------------------------------------------------------------------
# CLI integration tests using tmp_path
# ---------------------------------------------------------------------------

class TestMainCLI:
    def test_init_creates_dot_cat_folder(self, tmp_path):
        rc = init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01'])
        assert rc == 0
        assert (tmp_path / '.cat' / 'config.json').exists()
        assert (tmp_path / '.cat' / 'state.json').exists()
        assert (tmp_path / '.cat' / 'README.md').exists()

    def test_config_json_is_valid(self, tmp_path):
        init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01', '--repo-name', 'test-repo'])
        data = json.loads((tmp_path / '.cat' / 'config.json').read_text())
        assert data['cat_mission_id'] == 'MP-CAT-A012-4C01'
        assert data['repo_name'] == 'test-repo'

    def test_state_json_is_valid(self, tmp_path):
        import jsonschema
        init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01'])
        state = json.loads((tmp_path / '.cat' / 'state.json').read_text())
        schema = json.loads(init_mod.STATE_SCHEMA_PATH.read_text())
        jsonschema.validate(instance=state, schema=schema)

    def test_dry_run_creates_nothing(self, tmp_path):
        rc = init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01', '--dry-run'])
        assert rc == 0
        assert not (tmp_path / '.cat').exists()

    def test_missing_target_returns_2(self, tmp_path):
        rc = init_mod.main(['--target', str(tmp_path / 'nonexistent'), '--mission', 'MP-CAT-A012-4C01'])
        assert rc == 2

    def test_update_state_only_refreshes_state(self, tmp_path):
        init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01'])
        old_config = (tmp_path / '.cat' / 'config.json').read_text()
        rc = init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01', '--update-state'])
        assert rc == 0
        # config.json should be unchanged
        assert (tmp_path / '.cat' / 'config.json').read_text() == old_config

    def test_export_schemas_copies_files(self, tmp_path):
        rc = init_mod.main([
            '--target', str(tmp_path),
            '--mission', 'MP-CAT-A012-4C01',
            '--export-schemas', 'bead.schema.json',
        ])
        assert rc == 0
        assert (tmp_path / '.cat' / 'schemas' / 'bead.schema.json').exists()

    def test_repo_name_defaults_to_directory_name(self, tmp_path):
        init_mod.main(['--target', str(tmp_path), '--mission', 'MP-CAT-A012-4C01'])
        data = json.loads((tmp_path / '.cat' / 'config.json').read_text())
        assert data['repo_name'] == tmp_path.name


# ---------------------------------------------------------------------------
# cat_validate.py integration — adapter targets present
# ---------------------------------------------------------------------------

class TestValidateTargetsWired:
    def test_adapter_config_in_validation_targets(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import cat_validate
        target_names = [t[0] for t in cat_validate.VALIDATION_TARGETS]
        assert 'adapter config example' in target_names

    def test_adapter_state_in_validation_targets(self):
        import cat_validate
        target_names = [t[0] for t in cat_validate.VALIDATION_TARGETS]
        assert 'adapter state example' in target_names

    def test_adapter_fixture_files_exist(self):
        config_fixture = ROOT / 'tests' / 'fixtures' / 'adapter' / 'valid_config.json'
        state_fixture = ROOT / 'tests' / 'fixtures' / 'adapter' / 'valid_state.json'
        assert config_fixture.exists()
        assert state_fixture.exists()
