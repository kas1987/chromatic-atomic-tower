from pathlib import Path

import importlib.util


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_registry_audit_module():
    mod = _load_module('cat_registry_audit', 'scripts/cat_registry_audit.py')
    ok, errors = mod.audit(Path('missions/registry/MISSION_REGISTRY.yaml'))
    assert isinstance(ok, bool)
    assert isinstance(errors, list)
