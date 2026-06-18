#!/usr/bin/env python3
"""CAT Evidence Index — rebuild and validate evidence/manifest.yaml.

Usage:
  python scripts/cat_evidence_index.py --check          # validate existing manifest
  python scripts/cat_evidence_index.py --rebuild        # rebuild manifest from evidence/
  python scripts/cat_evidence_index.py --add <path> ... # add specific artifact(s)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from common import ROOT, load_yaml, write_yaml
except ModuleNotFoundError:
    from scripts.common import ROOT, load_yaml, write_yaml

MANIFEST_PATH = ROOT / 'evidence' / 'manifest.yaml'
SCHEMA_PATH = ROOT / 'schemas' / 'evidence_manifest.schema.json'
EVIDENCE_ROOT = ROOT / 'evidence'

VALID_ARTIFACT_TYPES = {
    'test_output', 'closeout_report', 'validation_log',
    'diff', 'screenshot', 'bundle', 'other',
}

SKIP_DIRS = {'snapshots/', 'bundles/', 'manifest.yaml'}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return 'error_reading_file'


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace('\\', '/')
    except ValueError:
        return str(path)


def load_schema() -> dict:
    if not SCHEMA_PATH.exists():
        return {}
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def validate_manifest(data: dict) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors: list[str] = []

    if not isinstance(data, dict):
        return ['manifest is not a dict']

    if 'schema_version' not in data:
        errors.append("missing required field: schema_version")

    entries = data.get('evidence', [])
    if not isinstance(entries, list):
        errors.append("'evidence' must be a list")
        return errors

    seen_ids: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry[{i}] is not a dict")
            continue
        for field in ('evidence_id', 'mission_id', 'bead_id', 'artifact_path',
                      'artifact_type', 'generated_at', 'sha256'):
            if field not in entry:
                errors.append(f"entry[{i}] missing required field: {field}")

        eid = entry.get('evidence_id', '')
        if eid in seen_ids:
            errors.append(f"duplicate evidence_id: {eid!r}")
        elif eid:
            seen_ids.add(eid)

        apath = entry.get('artifact_path', '')
        if apath and not (ROOT / apath).exists():
            errors.append(f"artifact_path does not exist on disk: {apath!r}")

        sha = entry.get('sha256', '')
        if sha and sha != 'placeholder_to_be_updated_by_cat_evidence_index':
            if len(sha) != 64 or not all(c in '0123456789abcdef' for c in sha):
                errors.append(f"entry[{i}] sha256 is not a valid hex digest: {sha!r}")

    return errors


def _guess_type(path: Path) -> str:
    name = path.name.lower()
    if 'test' in name or name.endswith(('-output.txt', '-tests.txt')):
        return 'test_output'
    if 'closeout' in name or 'report' in name:
        return 'closeout_report'
    if 'validate' in name or 'check' in name or 'guard' in name:
        return 'validation_log'
    if name.endswith('.diff') or name.endswith('.patch'):
        return 'diff'
    if name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return 'screenshot'
    if 'bundle' in str(path):
        return 'bundle'
    return 'other'


def rebuild_manifest(evidence_root: Path = EVIDENCE_ROOT) -> dict:
    """Scan evidence/ and build a fresh manifest from discovered artifacts."""
    entries: list[dict] = []
    seq = 0
    for path in sorted(evidence_root.rglob('*')):
        if not path.is_file():
            continue
        rel_str = rel(path)
        if any(skip in rel_str for skip in SKIP_DIRS):
            continue
        if path.suffix not in ('.txt', '.md', '.json', '.yaml', '.yml', '.diff', '.patch',
                                '.png', '.jpg', '.jpeg', '.gif', '.webp'):
            continue
        seq += 1
        entries.append({
            'evidence_id': f'EVD-REBUILD-{seq:04d}',
            'mission_id': 'UNKNOWN',
            'bead_id': 'UNKNOWN',
            'artifact_path': rel_str,
            'artifact_type': _guess_type(path),
            'generated_at': utc_now(),
            'validator': 'cat_evidence_index.py',
            'sha256': sha256_of(path),
        })
    return {
        'schema_version': '0.1.0',
        'generated_at': utc_now(),
        'evidence': entries,
    }


def update_sha256(data: dict) -> dict:
    """Replace placeholder sha256 values with real hashes."""
    for entry in data.get('evidence', []):
        apath = entry.get('artifact_path', '')
        if not apath:
            continue
        if entry.get('sha256') and 'placeholder' not in entry.get('sha256', ''):
            continue  # already hashed
        full = ROOT / apath
        if full.exists():
            entry['sha256'] = sha256_of(full)
    data['generated_at'] = utc_now()
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description='CAT Evidence Manifest index tool.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true',
                       help='Validate the existing manifest and exit nonzero if invalid.')
    group.add_argument('--rebuild', action='store_true',
                       help='Rebuild manifest.yaml by scanning evidence/.')
    group.add_argument('--update-hashes', action='store_true',
                       help='Update placeholder sha256 values with real hashes.')
    parser.add_argument('--manifest', default=str(MANIFEST_PATH),
                        help='Path to manifest.yaml (default: evidence/manifest.yaml)')
    args = parser.parse_args()

    manifest_path = Path(args.manifest)

    if args.check:
        if not manifest_path.exists():
            print(f"FAIL: manifest not found: {manifest_path}")
            return 1
        data = load_yaml(manifest_path) or {}
        errors = validate_manifest(data)
        if errors:
            print(f"FAIL: manifest has {len(errors)} error(s):")
            for e in errors:
                print(f"  - {e}")
            return 1
        count = len(data.get('evidence', []))
        print(f"OK: manifest valid, {count} evidence entries.")
        return 0

    if args.rebuild:
        data = rebuild_manifest()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_yaml(manifest_path, data)
        print(f"Rebuilt manifest: {len(data['evidence'])} entries -> {manifest_path}")
        return 0

    if args.update_hashes:
        if not manifest_path.exists():
            print(f"FAIL: manifest not found: {manifest_path}")
            return 1
        data = load_yaml(manifest_path) or {}
        updated = update_sha256(data)
        write_yaml(manifest_path, updated)
        print(f"Updated sha256 hashes in {manifest_path}")
        return 0

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
