"""Focused integration guards for the Official Beads + Wiskers cutover."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from scripts import cat_beads, cat_closeout, cat_resolve_go, cat_transition


def issue(**overrides):
    base = {
        'id': 'cat-test-1',
        'title': 'Test official Bead',
        'description': 'bounded test work',
        'status': 'open',
        'priority': 2,
        'created_at': '2026-08-15T00:00:00Z',
        'wisker': {
            'mission_id': 'MP-CAT-EXAMPLE-001',
            'objective': 'Run the bounded test.',
            'agent_role': 'Verifier',
            'autonomy_level': 'L1',
            'confidence': {'current': 90, 'minimum': 70},
            'risk': {'level': 'low', 'reversibility': 'reversible'},
            'allowed_paths': ['tests/'],
            'forbidden_paths': ['.beads/', 'archive/'],
            'tool_budget': {'max_tool_calls': 2},
            'definition_of_done': ['The test passes.'],
            'validation': [{'type': 'command', 'command': 'pytest -q', 'evidence_path': 'evidence/test.json'}],
            'stop_conditions': ['Digest changes.'],
            'required_output': ['evidence'],
        },
    }
    base.update(overrides)
    return base


def test_ready_selection_is_deterministic():
    selected = cat_beads.select_ready([
        issue(id='cat-z', priority=2, created_at='2026-08-15T01:00:00Z'),
        issue(id='cat-a', priority=1, created_at='2026-08-15T03:00:00Z'),
        issue(id='cat-b', priority=1, created_at='2026-08-15T02:00:00Z'),
    ])
    assert selected and selected['id'] == 'cat-b'


def test_official_bead_json_builds_schema_validated_wisker():
    wisker = cat_beads.build_wisker(issue(), '5ca98c47d86c55805917689b70aa3ee97f2426d8')
    schema = json.loads((cat_beads.ROOT / 'schemas/wisker.schema.json').read_text())
    jsonschema.validate(wisker, schema)
    assert wisker['bd_id'] == 'cat-test-1'
    assert 'status' not in wisker


def test_official_bead_id_is_accepted_by_evidence_schema():
    schema = json.loads((cat_beads.ROOT / 'schemas/evidence_bundle.schema.json').read_text())
    bundle = {
        'evidence_id': 'EB-CAT-LIVE-PLAYBOOK-001',
        'mission_id': 'MP-CAT-S001-4C01',
        'bead_id': 'cat-20i',
        'target_type': 'bead',
        'type': 'closeout',
        'summary': 'Official Beads closeout evidence.',
        'validation_result': 'passed',
        'required_artifacts': [{'path': 'playbooks/CAT_LIVE_OPERATIONS_PLAYBOOK.md', 'kind': 'artifact', 'required': True}],
        'supporting_artifacts': [],
        'created_by': 'pytest',
        'created_at': '2026-08-15T00:00:00Z',
        'learning_note': 'Official Beads IDs are authoritative.',
        'closeout_ready': True,
    }
    jsonschema.validate(bundle, schema)


def test_wisker_is_pinned_to_digest_and_git_sha():
    first = cat_beads.build_wisker(issue(), '5ca98c47d86c55805917689b70aa3ee97f2426d8')
    changed = cat_beads.build_wisker(issue(description='changed scope'), first['source_commit_sha'])
    assert first['source_bead_digest'] != changed['source_bead_digest']
    assert first['source_commit_sha'] == changed['source_commit_sha']


def test_claim_status_change_does_not_change_scope_digest():
    before = issue(status='open')
    after = issue(status='in_progress', updated_at='2026-08-15T01:00:00Z', assignee='agent')
    assert cat_beads.bead_digest(before) == cat_beads.bead_digest(after)


def test_repeated_packet_render_is_idempotent(tmp_path, monkeypatch):
    wisker = cat_beads.build_wisker(issue(), '5ca98c47d86c55805917689b70aa3ee97f2426d8')
    monkeypatch.setattr(cat_beads, 'ROOT', tmp_path)
    first = cat_beads.write_packet(wisker)
    first_mtime = first.stat().st_mtime_ns
    second = cat_beads.write_packet(wisker)
    assert first == second
    assert second.read_text() == first.read_text()
    assert second.stat().st_mtime_ns == first_mtime


def test_missing_wisker_metadata_fails_closed():
    with pytest.raises(cat_beads.BeadsCommandError, match='lacks Wisker metadata'):
        cat_beads.build_wisker({'id': 'cat-no-contract', 'title': 'No contract'}, '5ca98c47d86c55805917689b70aa3ee97f2426d8')


def test_forbidden_path_overlap_fails_closed():
    bad = issue()
    bad['wisker']['allowed_paths'] = ['.beads/']
    with pytest.raises(cat_beads.BeadsCommandError, match='protected path'):
        cat_beads.build_wisker(bad, '5ca98c47d86c55805917689b70aa3ee97f2426d8')


def test_missing_bd_fails_closed(monkeypatch):
    monkeypatch.setattr(cat_beads, '_candidate_commands', lambda: [])
    with pytest.raises(cat_beads.BeadsCommandError, match='official bd CLI not found'):
        cat_beads.ready_beads()


def test_malformed_bd_json_fails_closed(monkeypatch):
    monkeypatch.setattr(cat_beads, 'resolve_bd_command', lambda: ['bd'])
    class Result:
        returncode = 0
        stdout = '{not-json}'
        stderr = ''
    monkeypatch.setattr(cat_beads.subprocess, 'run', lambda *args, **kwargs: Result())
    with pytest.raises(cat_beads.BeadsCommandError, match='malformed JSON'):
        cat_beads.ready_beads()


def test_bead_transition_engine_refuses_parallel_lifecycle(monkeypatch):
    events = []
    monkeypatch.setattr(cat_transition, 'append_audit_event', lambda event, rules: events.append(event))
    code, event = cat_transition.apply_transition('bead', 'cat-test-1', 'closed', 'test', '', 'test', False, False)
    assert code == 1
    assert 'official Beads own Bead status' in event['message']
    assert events


def test_closeout_evidence_gate_runs_before_official_close(monkeypatch, tmp_path):
    monkeypatch.setattr(cat_closeout, 'ROOT', tmp_path)
    monkeypatch.setattr(cat_closeout, 'validate_bundle', lambda path: (False, ['invalid evidence'], {'target_type': 'bead', 'bead_id': 'cat-test-1'}))
    closed = []
    monkeypatch.setattr(cat_closeout, 'close_bead', lambda *args: closed.append(args))
    code, event = cat_closeout.run_closeout('bead', 'cat-test-1', 'closed', 'missing.yaml', 'test', 'test', False, False)
    assert code == 1
    assert not closed
    assert event['message'] == 'closeout blocked by evidence gate'


def test_runtime_scripts_do_not_read_legacy_active_yaml():
    scripts_dir = Path(__file__).parents[1] / 'scripts'
    offenders = []
    for path in scripts_dir.glob('*.py'):
        if 'beads/active' in path.read_text(encoding='utf-8'):
            offenders.append(path.name)
    assert not offenders, offenders


def test_first_beads_initialization_bootstraps_the_configured_remote():
    source = (Path(__file__).parents[1] / 'scripts/cat_beads_init.py').read_text(encoding='utf-8')
    assert "'init', '--remote', args.remote" in source
