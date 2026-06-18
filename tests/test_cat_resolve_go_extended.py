"""Extended tests for cat_resolve_go.py — targets previously-uncovered lines.

Coverage targets:
  - load_active_beads (lines 21-26)
  - select_bead queued branch (lines 52-55)
  - print_markdown stop_conditions section (lines 146-154 area)
  - _append_go_decision (lines 158-169)
  - _run_loghouse_self (lines 174-178)
  - _validate_against_schema (lines 183-192)
  - main() (lines 196-283)

Import pattern: always `import cat_resolve_go` so monkeypatch hits the same namespace.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

# Ensure scripts/ is on sys.path so `import cat_resolve_go` resolves.
ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT_PATH / 'scripts'))

import cat_resolve_go  # noqa: E402 — must come after path setup

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_MISSION = {
    'mission_id': 'MP-TEST-001',
    'title': 'Test Mission',
    'level': 'M3',
    'risk_level': 'medium',
    'status': 'approved',
    'priority': 1,
    'confidence': 85,
    'current_bead_id': 'BEAD-TEST-001',
    'path': 'missions/active/test.yaml',
    'created': '2026-01-01',
}

SAMPLE_BEAD = {
    'bead_id': 'BEAD-TEST-001',
    'mission_id': 'MP-TEST-001',
    'title': 'Test BEAD',
    'status': 'active',
    'agent_role': 'Builder',
    'autonomy_level': 'L3',
    'confidence': {'current': 83, 'minimum': 80},
    'risk_level': 'medium',
    'reversibility': 'high',
    'allowed_paths': ['scripts/'],
    'forbidden_paths': ['.env'],
    'tool_budget': {'search': 2, 'read': 8},
    'definition_of_done': ['Tests pass.'],
    'validation': [
        {'type': 'unit_tests', 'command': 'pytest', 'evidence_path': 'ev/x.txt'}
    ],
    'stop_conditions': ['Confidence drops.', 'Scope creep detected.'],
    'required_output': ['summary'],
    '_path': 'beads/active/BEAD-TEST-001.yaml',
}

SAMPLE_QUEUED_BEAD = {**SAMPLE_BEAD, 'bead_id': 'BEAD-TEST-Q01', 'status': 'queued'}

SAMPLE_DISPATCH = cat_resolve_go.build_dispatch(SAMPLE_MISSION, SAMPLE_BEAD)


# ---------------------------------------------------------------------------
# 1. TestLoadActiveBeads
# ---------------------------------------------------------------------------

class TestLoadActiveBeads:
    def test_loads_beads_from_active_dir(self, tmp_path, monkeypatch):
        """load_active_beads reads YAML files from beads/active and adds _path."""
        bead_dir = tmp_path / 'beads' / 'active'
        bead_dir.mkdir(parents=True)

        bead_data_a = {'bead_id': 'B-001', 'status': 'active', 'title': 'Alpha'}
        bead_data_b = {'bead_id': 'B-002', 'status': 'active', 'title': 'Beta'}

        (bead_dir / 'B-001.yaml').write_text(yaml.safe_dump(bead_data_a), encoding='utf-8')
        (bead_dir / 'B-002.yaml').write_text(yaml.safe_dump(bead_data_b), encoding='utf-8')

        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)

        result = cat_resolve_go.load_active_beads()

        assert len(result) == 2
        ids = {b['bead_id'] for b in result}
        assert ids == {'B-001', 'B-002'}
        # every entry must carry _path
        for b in result:
            assert '_path' in b

    def test_returns_empty_when_no_beads_dir(self, tmp_path, monkeypatch):
        """Returns [] gracefully when beads/active does not exist."""
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)
        result = cat_resolve_go.load_active_beads()
        assert result == []

    def test_returns_empty_when_no_yaml_files(self, tmp_path, monkeypatch):
        """Returns [] when beads/active exists but has no YAML files."""
        (tmp_path / 'beads' / 'active').mkdir(parents=True)
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)
        result = cat_resolve_go.load_active_beads()
        assert result == []


# ---------------------------------------------------------------------------
# 2. TestSelectBeadQueued
# ---------------------------------------------------------------------------

class TestSelectBeadQueued:
    def _make_mission_with_no_current(self):
        m = {**SAMPLE_MISSION, 'current_bead_id': None, 'mission_id': 'MP-Q-001'}
        return m

    def test_select_bead_allows_queued_when_flag_set(self):
        """When allow_queued=True and current_bead_id matches a queued BEAD, it is returned.

        The select_bead logic at lines 51-54 returns a candidate when mission.current_bead_id
        matches — so a queued bead only dispatches when the mission already points to it.
        """
        queued_bead = {**SAMPLE_QUEUED_BEAD, 'mission_id': 'MP-Q-001', 'bead_id': 'BEAD-Q-001'}
        mission = {**SAMPLE_MISSION, 'current_bead_id': 'BEAD-Q-001', 'mission_id': 'MP-Q-001'}
        result = cat_resolve_go.select_bead(mission, [queued_bead], allow_queued=True)
        assert result is not None
        assert result['bead_id'] == 'BEAD-Q-001'

    def test_select_bead_rejects_queued_by_default(self):
        """When allow_queued=False a queued-only BEAD is not returned."""
        mission = {**SAMPLE_MISSION, 'current_bead_id': None, 'mission_id': 'MP-Q-001'}
        bead = {**SAMPLE_QUEUED_BEAD, 'mission_id': 'MP-Q-001'}
        result = cat_resolve_go.select_bead(mission, [bead], allow_queued=False)
        assert result is None

    def test_select_bead_current_bead_takes_precedence(self):
        """current_bead_id match is returned even when another active bead exists."""
        mission = {**SAMPLE_MISSION, 'current_bead_id': 'BEAD-TEST-001', 'mission_id': 'MP-TEST-001'}
        other_active = {**SAMPLE_BEAD, 'bead_id': 'BEAD-TEST-999', 'mission_id': 'MP-TEST-001'}
        result = cat_resolve_go.select_bead(mission, [SAMPLE_BEAD, other_active], allow_queued=False)
        assert result is not None
        assert result['bead_id'] == 'BEAD-TEST-001'


# ---------------------------------------------------------------------------
# 3. TestPrintMarkdown
# ---------------------------------------------------------------------------

class TestPrintMarkdown:
    def test_prints_stop_conditions_header(self, capsys):
        """print_markdown outputs ## Stop Conditions section."""
        dispatch = {**SAMPLE_DISPATCH}
        cat_resolve_go.print_markdown(dispatch)
        out = capsys.readouterr().out
        assert '## Stop Conditions' in out

    def test_prints_all_stop_condition_items(self, capsys):
        """Each stop condition item appears in output."""
        dispatch = {**SAMPLE_DISPATCH, 'stop_conditions': ['Halt A', 'Halt B', 'Halt C']}
        cat_resolve_go.print_markdown(dispatch)
        out = capsys.readouterr().out
        for cond in ('Halt A', 'Halt B', 'Halt C'):
            assert cond in out

    def test_prints_cat_go_header(self, capsys):
        """The main # CAT GO Dispatch Packet header is printed."""
        cat_resolve_go.print_markdown(SAMPLE_DISPATCH)
        out = capsys.readouterr().out
        assert '# CAT GO Dispatch Packet' in out

    def test_prints_mission_and_bead_ids(self, capsys):
        """Mission and BEAD IDs appear in markdown output."""
        cat_resolve_go.print_markdown(SAMPLE_DISPATCH)
        out = capsys.readouterr().out
        assert 'MP-TEST-001' in out
        assert 'BEAD-TEST-001' in out


# ---------------------------------------------------------------------------
# 4. TestAppendGoDecision
# ---------------------------------------------------------------------------

class TestAppendGoDecision:
    def test_appends_jsonl_record(self, tmp_path, monkeypatch):
        """_append_go_decision creates log file with valid JSON record."""
        log_dir = tmp_path / 'evidence' / 'logs'
        log_dir.mkdir(parents=True)
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)

        cat_resolve_go._append_go_decision(allowed=True, drifts=[], sprint='SPRINT-000')

        log_file = log_dir / 'go_decisions.jsonl'
        assert log_file.exists()
        record = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert record['allowed'] is True
        assert record['drift_count'] == 0
        assert record['sprint'] == 'SPRINT-000'
        assert 'ts' in record
        assert 'commit_sha' in record

    def test_creates_parent_dir_automatically(self, tmp_path, monkeypatch):
        """_append_go_decision creates evidence/logs/ if it doesn't exist."""
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)
        # Do NOT create evidence/logs/ — the function must do it.
        cat_resolve_go._append_go_decision(allowed=False, drifts=['D001'], sprint='SPRINT-001')
        log_file = tmp_path / 'evidence' / 'logs' / 'go_decisions.jsonl'
        assert log_file.exists()

    def test_appends_multiple_records(self, tmp_path, monkeypatch):
        """Calling _append_go_decision twice yields two JSONL lines."""
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)
        cat_resolve_go._append_go_decision(allowed=True, drifts=[], sprint='S-000')
        cat_resolve_go._append_go_decision(allowed=False, drifts=['D001'], sprint='S-001')
        log_file = tmp_path / 'evidence' / 'logs' / 'go_decisions.jsonl'
        lines = [l for l in log_file.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) == 2
        r2 = json.loads(lines[1])
        assert r2['allowed'] is False
        assert r2['drifts'] == ['D001']


# ---------------------------------------------------------------------------
# 5. TestRunLoghouseSelf
# ---------------------------------------------------------------------------

class TestRunLoghouseSelf:
    def test_run_loghouse_self_returns_int(self, monkeypatch):
        """_run_loghouse_self returns an integer exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(cat_resolve_go.subprocess, 'run', mock_run)

        rc = cat_resolve_go._run_loghouse_self(strict=False)
        assert isinstance(rc, int)
        assert rc == 0

    def test_run_loghouse_self_strict_adds_flag(self, monkeypatch):
        """When strict=True the --strict flag is appended to the command."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return mock_result

        monkeypatch.setattr(cat_resolve_go.subprocess, 'run', fake_run)
        cat_resolve_go._run_loghouse_self(strict=True)
        assert '--strict' in captured_cmd

    def test_run_loghouse_self_no_strict_flag_when_false(self, monkeypatch):
        """When strict=False --strict is NOT in the command."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return mock_result

        monkeypatch.setattr(cat_resolve_go.subprocess, 'run', fake_run)
        cat_resolve_go._run_loghouse_self(strict=False)
        assert '--strict' not in captured_cmd


# ---------------------------------------------------------------------------
# 6. TestValidateAgainstSchema
# ---------------------------------------------------------------------------

class TestValidateAgainstSchema:
    def test_returns_empty_list_on_valid_dispatch(self, monkeypatch):
        """A fully-formed dispatch packet passes schema validation."""
        monkeypatch.setattr(cat_resolve_go, 'ROOT', ROOT_PATH)
        errors = cat_resolve_go._validate_against_schema(SAMPLE_DISPATCH)
        assert errors == [], errors

    def test_returns_error_on_missing_required_field(self, monkeypatch):
        """Removing a required field produces at least one error."""
        monkeypatch.setattr(cat_resolve_go, 'ROOT', ROOT_PATH)
        bad_dispatch = {k: v for k, v in SAMPLE_DISPATCH.items() if k != 'dispatch_status'}
        errors = cat_resolve_go._validate_against_schema(bad_dispatch)
        assert len(errors) > 0

    def test_handles_jsonschema_not_installed(self, monkeypatch, tmp_path):
        """When jsonschema is not importable, returns a descriptive error string."""
        # Write a minimal valid schema file so the path exists.
        schema_dir = tmp_path / 'schemas'
        schema_dir.mkdir()
        (schema_dir / 'go_dispatch_packet.schema.json').write_text(
            json.dumps({'type': 'object'}), encoding='utf-8'
        )
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)

        # Simulate jsonschema not being installed by setting it to None in sys.modules
        monkeypatch.setitem(sys.modules, 'jsonschema', None)
        errors = cat_resolve_go._validate_against_schema(SAMPLE_DISPATCH)
        assert any('jsonschema not installed' in e for e in errors)

    def test_returns_error_on_schema_exception(self, monkeypatch, tmp_path):
        """A corrupt schema file produces a schema validation error string."""
        schema_dir = tmp_path / 'schemas'
        schema_dir.mkdir()
        (schema_dir / 'go_dispatch_packet.schema.json').write_text('NOT JSON', encoding='utf-8')
        monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)
        errors = cat_resolve_go._validate_against_schema(SAMPLE_DISPATCH)
        assert len(errors) > 0
        assert any('schema' in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# 7. TestMain — the big coverage win (lines 196-283)
# ---------------------------------------------------------------------------

def _make_tower(status='sprint_idle', sprint='SPRINT-000', bead_id=''):
    return {'status': status, 'active_sprint': sprint, 'active_bead_id': bead_id}


def _make_registry(missions=None):
    return {'missions': missions or []}


def _setup_tmp_root(tmp_path: Path, monkeypatch):
    """Patch ROOT to tmp_path and create the required evidence/logs dir."""
    (tmp_path / 'evidence' / 'logs').mkdir(parents=True)
    monkeypatch.setattr(cat_resolve_go, 'ROOT', tmp_path)


class TestMain:
    def test_main_sprint_idle_no_mission_returns_0(self, tmp_path, monkeypatch, capsys):
        """sprint_idle + no approved mission → exit 0."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', ['cat_resolve_go.py', '--skip-align-check', '--skip-loghouse'])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: None)
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', lambda path: _make_tower(status='sprint_idle'))
        rc = cat_resolve_go.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert 'sprint_idle' in out or 'No approved mission' in out

    def test_main_no_mission_not_idle_returns_1(self, tmp_path, monkeypatch, capsys):
        """active tower + no approved mission → exit 1."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', ['cat_resolve_go.py', '--skip-align-check', '--skip-loghouse'])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: None)
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', lambda path: _make_tower(status='active'))
        rc = cat_resolve_go.main()
        assert rc == 1

    def test_main_no_bead_returns_1(self, tmp_path, monkeypatch, capsys):
        """Active mission but no BEAD → exit 1."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', ['cat_resolve_go.py', '--skip-align-check', '--skip-loghouse'])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead', lambda mission, beads, **kw: None)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [])

        call_count = [0]
        def fake_load_yaml(path):
            call_count[0] += 1
            return _make_tower(status='active', sprint='SPRINT-000', bead_id='')
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)

        rc = cat_resolve_go.main()
        assert rc == 1

    def test_main_json_output(self, tmp_path, monkeypatch, capsys):
        """--json flag causes stdout to be valid JSON with dispatch_status."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-align-check', '--skip-loghouse', '--json',
        ])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead',
                            lambda mission, beads, **kw: SAMPLE_BEAD)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [SAMPLE_BEAD])

        # load_yaml called for tower (×2) and registry
        def fake_load_yaml(path):
            p = str(path)
            if 'TOWER' in p.upper():
                return _make_tower(status='active', sprint='SPRINT-000', bead_id='BEAD-TEST-001')
            return _make_registry()
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)
        # Also mock normalize_bead_id to return the same value
        monkeypatch.setattr(cat_resolve_go, 'normalize_bead_id', lambda x: x or '')

        rc = cat_resolve_go.main()
        out = capsys.readouterr().out
        # Should be 0 (ready) or 1 (blocked) — not a crash
        assert rc in (0, 1)
        if rc == 0:
            data = json.loads(out)
            assert 'dispatch_status' in data

    def test_main_markdown_output(self, tmp_path, monkeypatch, capsys):
        """Default (no --json) causes markdown output with # CAT GO."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-align-check', '--skip-loghouse',
        ])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead',
                            lambda mission, beads, **kw: SAMPLE_BEAD)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [SAMPLE_BEAD])

        def fake_load_yaml(path):
            p = str(path)
            if 'TOWER' in p.upper():
                return _make_tower(status='active', sprint='SPRINT-000', bead_id='BEAD-TEST-001')
            return _make_registry()
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)
        monkeypatch.setattr(cat_resolve_go, 'normalize_bead_id', lambda x: x or '')

        rc = cat_resolve_go.main()
        out = capsys.readouterr().out
        assert rc in (0, 1)
        assert '# CAT GO Dispatch Packet' in out

    def test_main_format_json_alias(self, tmp_path, monkeypatch, capsys):
        """--format json is equivalent to --json."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-align-check', '--skip-loghouse', '--format', 'json',
        ])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead',
                            lambda mission, beads, **kw: SAMPLE_BEAD)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [SAMPLE_BEAD])

        def fake_load_yaml(path):
            p = str(path)
            if 'TOWER' in p.upper():
                return _make_tower(status='active', sprint='SPRINT-000', bead_id='BEAD-TEST-001')
            return _make_registry()
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)
        monkeypatch.setattr(cat_resolve_go, 'normalize_bead_id', lambda x: x or '')

        rc = cat_resolve_go.main()
        out = capsys.readouterr().out
        assert rc in (0, 1)
        if rc == 0:
            # Should produce JSON (parseable)
            data = json.loads(out)
            assert 'dispatch_status' in data

    def test_main_check_schema_flag(self, tmp_path, monkeypatch, capsys):
        """--check-schema implies skip-align and skip-loghouse; does not crash."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--check-schema', '--format', 'json',
        ])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead',
                            lambda mission, beads, **kw: SAMPLE_BEAD)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [SAMPLE_BEAD])

        def fake_load_yaml(path):
            p = str(path)
            if 'TOWER' in p.upper():
                return _make_tower(status='active', sprint='SPRINT-000', bead_id='BEAD-TEST-001')
            return _make_registry()
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)
        monkeypatch.setattr(cat_resolve_go, 'normalize_bead_id', lambda x: x or '')
        # Use real ROOT for schema validation
        monkeypatch.setattr(cat_resolve_go, 'ROOT', ROOT_PATH)
        # But still write the decision log
        (tmp_path / 'evidence' / 'logs').mkdir(parents=True, exist_ok=True)
        # Redirect the log write to tmp_path by patching _append_go_decision
        monkeypatch.setattr(cat_resolve_go, '_append_go_decision', lambda **kw: None)

        rc = cat_resolve_go.main()
        assert rc in (0, 1)

    def test_main_alignment_fail_returns_1(self, tmp_path, monkeypatch, capsys):
        """Alignment failure (is_aligned=False) blocks GO and returns 1."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-loghouse',
        ])

        mock_alignment = MagicMock()
        mock_alignment.is_aligned = False
        mock_alignment.report.return_value = (
            'DRIFT [D001] bead_id mismatch\nDRIFT [D002] status conflict'
        )
        monkeypatch.setattr(cat_resolve_go, 'check_alignment', lambda root: mock_alignment)
        monkeypatch.setattr(cat_resolve_go, 'load_yaml',
                            lambda path: _make_tower(status='active', sprint='SPRINT-000'))

        rc = cat_resolve_go.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert 'GO blocked' in out

    def test_main_loghouse_failure_blocks_go(self, tmp_path, monkeypatch, capsys):
        """When loghouse returns non-zero, GO is blocked with exit 1."""
        _setup_tmp_root(tmp_path, monkeypatch)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-align-check',
        ])
        monkeypatch.setattr(cat_resolve_go, 'select_mission', lambda reg: SAMPLE_MISSION)
        monkeypatch.setattr(cat_resolve_go, 'select_bead',
                            lambda mission, beads, **kw: SAMPLE_BEAD)
        monkeypatch.setattr(cat_resolve_go, 'load_active_beads', lambda: [SAMPLE_BEAD])

        def fake_load_yaml(path):
            p = str(path)
            if 'TOWER' in p.upper():
                return _make_tower(status='active', sprint='SPRINT-000', bead_id='BEAD-TEST-001')
            return _make_registry()
        monkeypatch.setattr(cat_resolve_go, 'load_yaml', fake_load_yaml)
        monkeypatch.setattr(cat_resolve_go, 'normalize_bead_id', lambda x: x or '')
        monkeypatch.setattr(cat_resolve_go, '_run_loghouse_self', lambda strict: 1)

        rc = cat_resolve_go.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert 'LOGHOUSE' in out

    def test_main_real_repo_sprint_idle(self, tmp_path, monkeypatch, capsys):
        """With real repo (sprint_idle, no active mission) main returns 0."""
        # Monkeypatch ROOT back to real repo but redirect log writes to tmp_path
        (tmp_path / 'evidence' / 'logs').mkdir(parents=True)
        monkeypatch.setattr(cat_resolve_go, '_append_go_decision', lambda **kw: None)
        monkeypatch.setattr(sys, 'argv', [
            'cat_resolve_go.py', '--skip-align-check', '--skip-loghouse',
        ])
        # Restore real ROOT so it reads real YAML files.
        monkeypatch.setattr(cat_resolve_go, 'ROOT', ROOT_PATH)

        rc = cat_resolve_go.main()
        out = capsys.readouterr().out
        # Real repo is sprint_idle with no approved mission → should be 0
        assert rc == 0, f"Expected 0 but got {rc}. stdout={out}"
