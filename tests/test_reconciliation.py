from pathlib import Path

import importlib.util


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_audit_passes():
    mod = _load_module('cat_registry_audit', 'scripts/cat_registry_audit.py')
    ok, errors = mod.audit(
        Path('missions/registry/MISSION_REGISTRY.yaml'),
        Path('docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml'),
    )
    assert ok, errors


def test_reconciliation_passes():
    mod = _load_module('cat_reconcile', 'scripts/cat_reconcile.py')
    report = mod.check(
        Path('docs/reconciliation/LIVE_REPO_ALIGNMENT_TARGET.yaml'),
        Path.cwd(),
    )
    assert report['status'] == 'passed', report


def test_roadmap_contains_canonical_sprints():
    text = Path('CAT_ROADMAP.md').read_text(encoding='utf-8')
    for term in [
        'Evidence Gate',
        'CI Governance',
        'Repo Alignment and Mission Packet Reconciliation',
        'GitHub Bridge + PR Governance',
        'Agent Scorecard Automation',
        'CAT Portable Project Adapter',
    ]:
        assert term in text
