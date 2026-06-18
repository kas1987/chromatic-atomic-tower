#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from common import ROOT, load_yaml, rel, validate_with_schema
from cat_branch_hygiene import find_root_hygiene_issues, load_root_allowlist

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

NEW_MISSION_ID_RE = re.compile(r'^MP-CAT-[SABC][0-9]{3}-[1-4]C[0-9]{2}$')
LEGACY_MISSION_ID_RE = re.compile(r'^MP-CAT-([0-9]{3})$')
EXAMPLE_MISSION_ID_RE = re.compile(r'^MP-CAT-EXAMPLE-[A-Z0-9-]+$')

NEW_BEAD_ID_RE = re.compile(r'^BEAD-CAT-[SABC][0-9]{3}-[1-4]C[0-9]{2}-[0-9]{2}$')
LEGACY_BEAD_ID_RE = re.compile(r'^BEAD-CAT-[0-9]{3}-[0-9]{3}$')
LEGACY_BEAD_EXAMPLE_RE = re.compile(r'^BEAD-CAT-(EXAMPLE-[0-9]+|[0-9]{3}-CLOSEOUT-EXAMPLE)$')

NEW_WORK_LEGACY_NUMERIC_CUTOFF = 6


def _legacy_mission_number(mission_id: str) -> int | None:
    match = LEGACY_MISSION_ID_RE.match(mission_id)
    if not match:
        return None
    return int(match.group(1))


def _is_new_mission_id(mission_id: str) -> bool:
    return bool(NEW_MISSION_ID_RE.match(mission_id))


def _is_legacy_allowed_mission_id(mission_id: str) -> bool:
    if EXAMPLE_MISSION_ID_RE.match(mission_id):
        return True
    mission_num = _legacy_mission_number(mission_id)
    return mission_num is not None and mission_num < NEW_WORK_LEGACY_NUMERIC_CUTOFF


def _is_new_bead_id(bead_id: str) -> bool:
    return bool(NEW_BEAD_ID_RE.match(bead_id))


def _is_legacy_allowed_bead_id(bead_id: str) -> bool:
    return bool(LEGACY_BEAD_ID_RE.match(bead_id) or LEGACY_BEAD_EXAMPLE_RE.match(bead_id))


def validate_id_policy(kind: str, instance: dict, file_path: Path) -> list[str]:
    if 'templates' in file_path.parts:
        return []

    errors: list[str] = []

    if kind == 'mission':
        mission_id = str(instance.get('mission_id', '')).strip()
        if _is_new_mission_id(mission_id) or _is_legacy_allowed_mission_id(mission_id):
            return []

        mission_num = _legacy_mission_number(mission_id)
        if mission_num is not None and mission_num >= NEW_WORK_LEGACY_NUMERIC_CUTOFF:
            errors.append(
                f'mission_id {mission_id} is legacy numeric at or above cutover; '
                'use MP-CAT-A006-4C01 style (tier in [S,A,B,C])'
            )
            return errors

        errors.append(
            f'mission_id {mission_id} is invalid; expected MP-CAT-A006-4C01 style '
            '(tier in [S,A,B,C]) or grandfathered legacy mission id below cutover'
        )
        return errors

    if kind == 'bead':
        bead_id = str(instance.get('bead_id', '')).strip()
        mission_id = str(instance.get('mission_id', '')).strip()

        mission_new = _is_new_mission_id(mission_id)
        mission_legacy_num = _legacy_mission_number(mission_id)
        mission_legacy_allowed = _is_legacy_allowed_mission_id(mission_id)

        if not (mission_new or mission_legacy_allowed):
            if mission_legacy_num is not None and mission_legacy_num >= NEW_WORK_LEGACY_NUMERIC_CUTOFF:
                errors.append(
                    f'mission_id {mission_id} is legacy numeric at or above cutover; '
                    'use MP-CAT-A006-4C01 style (tier in [S,A,B,C])'
                )
            else:
                errors.append(
                    f'mission_id {mission_id} is invalid for bead; expected new mission id '
                    'or grandfathered legacy mission id below cutover'
                )

        bead_new = _is_new_bead_id(bead_id)
        bead_legacy_allowed = _is_legacy_allowed_bead_id(bead_id)

        if mission_new:
            if not bead_new:
                errors.append(
                    f'bead_id {bead_id} is legacy under new-format mission {mission_id}; '
                    'use mission-stem bead style, e.g. BEAD-CAT-A006-4C01-01'
                )
            return errors

        if mission_legacy_num is not None and mission_legacy_num >= NEW_WORK_LEGACY_NUMERIC_CUTOFF:
            if not bead_new:
                errors.append(
                    f'bead_id {bead_id} must use new format because mission {mission_id} '
                    'is at or above legacy cutover'
                )
            return errors

        if not (bead_new or bead_legacy_allowed):
            errors.append(
                f'bead_id {bead_id} is invalid; expected BEAD-CAT-A006-4C01-01 style '
                'or grandfathered legacy bead id'
            )

    return errors


def validate_file(kind: str, file_path: Path, schema_path: Path) -> tuple[bool, list[str]]:
    try:
        instance = load_yaml(file_path)
    except Exception as exc:  # pragma: no cover
        return False, [f'could not parse YAML: {exc}']
    errors = validate_with_schema(instance, schema_path)
    if not errors and isinstance(instance, dict):
        errors.extend(validate_id_policy(kind, instance, file_path))
    return not errors, errors


def validate_root_hygiene(root: Path = ROOT) -> tuple[bool, list[str]]:
    allowlist_path = root / 'gates/hygiene/root_allowlist.yaml'
    if not allowlist_path.exists():
        return False, [f'root allowlist missing: {rel(allowlist_path)}']

    allowlist = load_root_allowlist(allowlist_path)
    issues = find_root_hygiene_issues(root, allowlist)
    return not issues, issues


def resolve_root_hygiene_mode(cli_mode: str | None = None) -> str:
    mode = (cli_mode or os.environ.get('CAT_ROOT_HYGIENE_MODE') or 'enforce').strip().lower()
    if mode not in {'enforce', 'warn', 'off'}:
        return 'enforce'
    return mode


def validate_all(include_templates: bool = True, root_hygiene_mode: str = 'enforce') -> int:
    failures = 0
    targets: list[tuple[str, Path, Path]] = list(VALIDATION_TARGETS)
    mode = resolve_root_hygiene_mode(root_hygiene_mode)

    if mode == 'off':
        print('SKIP root hygiene: enforcement disabled (mode=off)')
    else:
        root_ok, root_issues = validate_root_hygiene(ROOT)
        if root_ok:
            print('PASS root hygiene: root entries satisfy allowlist')
        elif mode == 'warn':
            print('WARN root hygiene: root contains non-allowlisted entries (non-blocking)')
            for issue in root_issues:
                print(f'  - {issue}')
        else:
            failures += 1
            print('FAIL root hygiene: root contains non-allowlisted entries')
            for issue in root_issues:
                print(f'  - {issue}')

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
    parser.add_argument(
        '--root-hygiene-mode',
        choices=['enforce', 'warn', 'off'],
        default=None,
        help='Root hygiene enforcement mode (default from CAT_ROOT_HYGIENE_MODE or enforce).',
    )
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
        return validate_all(
            include_templates=not args.no_templates,
            root_hygiene_mode=resolve_root_hygiene_mode(args.root_hygiene_mode),
        )

    parser.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
