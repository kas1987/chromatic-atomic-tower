#!/usr/bin/env python3
"""
cat_adapter_init.py — Generate or update a .cat/ adapter folder in a target project.

Usage:
  python scripts/cat_adapter_init.py --target <dir> [options]

Options:
  --target DIR          Project root to initialize (default: current directory)
  --mission MISSION_ID  CAT mission ID to link
  --repo-name NAME      Repository name (default: target directory name)
  --sync-mode MODE      read_only | manual (default: read_only)
  --update-state        Refresh .cat/state.json from TOWER_STATE + MISSION_REGISTRY
  --export-schemas NAMES  Comma-separated schema filenames to copy into .cat/schemas/
  --dry-run             Print what would be created without writing

Exit codes: 0 success · 1 validation error · 2 target-not-found
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import timezone, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

CONFIG_SCHEMA_PATH = ROOT / 'schemas' / 'cat_adapter_config.schema.json'
STATE_SCHEMA_PATH = ROOT / 'schemas' / 'cat_adapter_state.schema.json'
TOWER_STATE_PATH = ROOT / 'state' / 'TOWER_STATE.yaml'
MISSION_REGISTRY_PATH = ROOT / 'missions' / 'registry' / 'MISSION_REGISTRY.yaml'

README_TEMPLATE = """\
# .cat — CAT Portable Adapter

This folder links the project to a Chromatic Atomic Tower (CAT) mission.

## Files

| File | Purpose |
|------|---------|
| `config.json` | Adapter configuration (static; edit once) |
| `state.json` | Live state snapshot (updated on each BEAD transition) |

## Updating state

After each BEAD transition run:

```bash
python <cat-root>/scripts/cat_adapter_init.py --target . --update-state
```

Or update `state.json` manually — it validates against
`schemas/cat_adapter_state.schema.json` in the CAT repository.

## Documentation

See `docs/architecture/CAT_PORTABLE_ADAPTER.md` in the CAT repository.
"""


def _validate(instance: dict, schema_path: Path) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    try:
        import jsonschema
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        validator = jsonschema.Draft202012Validator(schema)
        return [e.message for e in validator.iter_errors(instance)]
    except Exception as exc:
        return [str(exc)]


def _load_yaml_simple(path: Path) -> dict:
    """Minimal YAML loader (key: value lines only, no deps beyond stdlib)."""
    try:
        import yaml  # type: ignore
        with open(path, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _active_mission_id() -> str:
    tower = _load_yaml_simple(TOWER_STATE_PATH)
    return (tower.get('active_mission_id') or '').strip()


def _mission_entry(mission_id: str) -> dict:
    registry = _load_yaml_simple(MISSION_REGISTRY_PATH)
    for m in (registry.get('missions') or []):
        if m.get('mission_id') == mission_id:
            return m
    return {}


def build_config(mission_id: str, repo_name: str, sync_mode: str) -> dict:
    return {
        "adapter_version": "1.0",
        "cat_mission_id": mission_id,
        "repo_name": repo_name,
        "sync_mode": sync_mode,
    }


def build_state(mission_id: str) -> dict:
    entry = _mission_entry(mission_id)
    return {
        "snapshot_timestamp": _now_iso(),
        "cat_mission_id": mission_id,
        "mission_status": entry.get('status') or 'unknown',
        "active_bead_id": entry.get('current_bead_id') or None,
        "last_sync": None,
    }


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f'  [dry-run] would write {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'  wrote {path}')


def export_schemas(cat_folder: Path, names: list[str], dry_run: bool) -> int:
    schemas_dir = cat_folder / 'schemas'
    errors = 0
    for name in names:
        src = ROOT / 'schemas' / name
        if not src.exists():
            print(f'  WARNING: schema {name} not found in {ROOT}/schemas/ — skipped')
            errors += 1
            continue
        dst = schemas_dir / name
        if dry_run:
            print(f'  [dry-run] would copy {src} → {dst}')
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f'  exported {dst}')
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description='Generate or update a .cat/ adapter folder.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--target', default='.', help='Project root directory')
    parser.add_argument('--mission', default='', help='CAT mission ID to link')
    parser.add_argument('--repo-name', default='', help='Repository name')
    parser.add_argument('--sync-mode', default='read_only', choices=['read_only', 'manual'])
    parser.add_argument('--update-state', action='store_true', help='Refresh state.json only')
    parser.add_argument('--export-schemas', default='', help='Comma-separated schema filenames')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f'ERROR: target directory {target} does not exist', file=sys.stderr)
        return 2

    mission_id = (args.mission or _active_mission_id()).strip()
    if not mission_id:
        print('ERROR: --mission required (or set active_mission_id in TOWER_STATE.yaml)', file=sys.stderr)
        return 1

    repo_name = args.repo_name or target.name
    cat_folder = target / '.cat'

    print(f'cat_adapter_init — target={target}  mission={mission_id}')

    # --update-state: only refresh state.json
    if args.update_state:
        state = build_state(mission_id)
        errors = _validate(state, STATE_SCHEMA_PATH)
        if errors:
            for e in errors:
                print(f'  SCHEMA ERROR: {e}')
            return 1
        write_file(cat_folder / 'state.json', json.dumps(state, indent=2), args.dry_run)
        return 0

    # Full init
    config = build_config(mission_id, repo_name, args.sync_mode)
    state = build_state(mission_id)

    config_errors = _validate(config, CONFIG_SCHEMA_PATH)
    state_errors = _validate(state, STATE_SCHEMA_PATH)
    if config_errors or state_errors:
        for e in config_errors + state_errors:
            print(f'  SCHEMA ERROR: {e}')
        return 1

    write_file(cat_folder / 'config.json', json.dumps(config, indent=2), args.dry_run)
    write_file(cat_folder / 'state.json', json.dumps(state, indent=2), args.dry_run)
    write_file(cat_folder / 'README.md', README_TEMPLATE, args.dry_run)

    if args.export_schemas:
        names = [n.strip() for n in args.export_schemas.split(',') if n.strip()]
        export_schemas(cat_folder, names, args.dry_run)

    return 0


if __name__ == '__main__':
    sys.exit(main())
