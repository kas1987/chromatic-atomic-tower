#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_yaml, rel, validate_with_schema

VALIDATION_TARGETS = [
    ('mission registry', ROOT / 'missions/registry/MISSION_REGISTRY.yaml', ROOT / 'schemas/mission_registry.schema.json'),
    ('agent registry', ROOT / 'agents/registry/AGENT_REGISTRY.yaml', ROOT / 'schemas/agent.schema.json'),
    ('tower state', ROOT / 'state/TOWER_STATE.yaml', ROOT / 'schemas/tower_state.schema.json'),
]

MISSION_PATTERNS = [
    'missions/active/*.yaml',
    'missions/backlog/*.yaml',
    'missions/examples/*.yaml',
]

BEAD_PATTERNS = [
    'beads/active/*.yaml',
    'beads/examples/*.yaml',
]

EVIDENCE_BUNDLE_PATTERNS = [
    'evidence/bundles/examples/*.yaml',
    'evidence/bundles/generated/*.yaml',
]

# Templates include placeholder IDs and should validate as structural samples.
TEMPLATE_PATTERNS = [
    ('mission template', 'missions/templates/*.yaml', ROOT / 'schemas/mission.schema.json'),
    ('bead template', 'beads/templates/*.yaml', ROOT / 'schemas/bead.schema.json'),
]


def validate_file(kind: str, file_path: Path, schema_path: Path) -> tuple[bool, list[str]]:
    try:
        instance = load_yaml(file_path)
    except Exception as exc:  # pragma: no cover
        return False, [f'could not parse YAML: {exc}']
    errors = validate_with_schema(instance, schema_path)
    return not errors, errors


def validate_all(include_templates: bool = True) -> int:
    failures = 0
    targets: list[tuple[str, Path, Path]] = list(VALIDATION_TARGETS)

    for pattern in MISSION_PATTERNS:
        for file_path in sorted(ROOT.glob(pattern)):
            targets.append(('mission', file_path, ROOT / 'schemas/mission.schema.json'))

    for pattern in BEAD_PATTERNS:
        for file_path in sorted(ROOT.glob(pattern)):
            targets.append(('bead', file_path, ROOT / 'schemas/bead.schema.json'))

    for pattern in EVIDENCE_BUNDLE_PATTERNS:
        for file_path in sorted(ROOT.glob(pattern)):
            targets.append(('evidence bundle', file_path, ROOT / 'schemas/evidence_bundle.schema.json'))

    if include_templates:
        for kind, pattern, schema in TEMPLATE_PATTERNS:
            for file_path in sorted(ROOT.glob(pattern)):
                targets.append((kind, file_path, schema))

    for kind, file_path, schema_path in targets:
        ok, errors = validate_file(kind, file_path, schema_path)
        if ok:
            print(f'PASS {kind}: {rel(file_path)}')
        else:
            failures += 1
            print(f'FAIL {kind}: {rel(file_path)}')
            for error in errors:
                print(f'  - {error}')

    if failures:
        print(f'CAT validation failed: {failures} file(s) failed.')
        return 1

    print('CAT validation passed.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate CAT YAML contracts against JSON schemas.')
    parser.add_argument('--all', action='store_true', help='Validate all known CAT contract files.')
    parser.add_argument('--no-templates', action='store_true', help='Skip template validation.')
    parser.add_argument('--file', type=str, help='Validate one file. Schema inferred by path.')
    args = parser.parse_args()

    if args.file:
        file_path = (ROOT / args.file).resolve()
        if 'beads' in file_path.parts:
            schema = ROOT / 'schemas/bead.schema.json'
            kind = 'bead'
        elif 'missions/registry' in str(file_path):
            schema = ROOT / 'schemas/mission_registry.schema.json'
            kind = 'mission registry'
        elif 'missions' in file_path.parts:
            schema = ROOT / 'schemas/mission.schema.json'
            kind = 'mission'
        elif 'evidence/bundles' in str(file_path):
            schema = ROOT / 'schemas/evidence_bundle.schema.json'
            kind = 'evidence bundle'
        elif file_path.name == 'TOWER_STATE.yaml':
            schema = ROOT / 'schemas/tower_state.schema.json'
            kind = 'tower state'
        else:
            print('Could not infer schema for file.')
            return 2
        ok, errors = validate_file(kind, file_path, schema)
        if ok:
            print(f'PASS {kind}: {rel(file_path)}')
            return 0
        print(f'FAIL {kind}: {rel(file_path)}')
        for error in errors:
            print(f'  - {error}')
        return 1

    if args.all:
        return validate_all(include_templates=not args.no_templates)

    parser.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
