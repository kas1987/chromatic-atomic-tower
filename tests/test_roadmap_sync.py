from pathlib import Path

import importlib.util


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_roadmap_sync_passes():
    mod = _load_module('cat_roadmap_sync', 'scripts/cat_roadmap_sync.py')
    text = Path('CAT_ROADMAP.md').read_text(encoding='utf-8')
    missing = [t for t in mod.TERMS if t not in text]
    assert not missing, missing
