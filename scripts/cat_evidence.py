#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from common import ROOT, load_yaml, write_yaml, validate_with_schema, rel
except ModuleNotFoundError:  # pragma: no cover
    from scripts.common import ROOT, load_yaml, write_yaml, validate_with_schema, rel

RULES_PATH = ROOT / 'gates/evidence/EVIDENCE_GATE_RULES.yaml'
SCHEMA_PATH = ROOT / 'schemas/evidence_bundle.schema.json'


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_rules() -> dict[str, Any]:
    return load_yaml(RULES_PATH)


def bundle_path(bundle: str) -> Path:
    path = Path(bundle)
    if not path.is_absolute():
        path = ROOT / path
    return path


def validate_bundle(bundle_file: Path) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    data = load_yaml(bundle_file)
    schema_errors = validate_with_schema(data, SCHEMA_PATH)
    errors.extend(f'schema: {item}' for item in schema_errors)

    rules = load_rules()
    target_type = data.get('target_type')
    target_rules = rules.get('targets', {}).get(target_type, {})

    for field in target_rules.get('required_fields', []):
        value = data.get(field)
        if value is None or value == '' or value == []:
            errors.append(f'required field missing or empty: {field}')

    if target_type == 'bead' and not data.get('bead_id'):
        errors.append('bead evidence requires bead_id')

    learning_required = bool(target_rules.get('require_learning_note'))
    if learning_required and not str(data.get('learning_note', '')).strip():
        errors.append('learning_note is required')

    require_artifacts = bool(target_rules.get('require_required_artifacts_exist'))
    if require_artifacts:
        for artifact in data.get('required_artifacts', []):
            if artifact.get('required'):
                artifact_path = ROOT / artifact.get('path', '')
                if not artifact_path.exists():
                    errors.append(f'missing required artifact: {artifact.get("path")}')

    validation_result = data.get('validation_result')
    if validation_result in set(rules.get('validation_results', {}).get('blocking', [])):
        errors.append(f'blocking validation result: {validation_result}')

    for artifact in data.get('required_artifacts', []):
        if artifact.get('required') and artifact.get('validation_result') in {'failed', 'blocked'}:
            errors.append(f"required artifact has blocking validation: {artifact.get('path')} -> {artifact.get('validation_result')}")

    if data.get('closeout_ready') is not True:
        errors.append('closeout_ready must be true')

    return not errors, errors, data


def summarize_result(ok: bool, errors: list[str], data: dict[str, Any], bundle_file: Path) -> dict[str, Any]:
    return {
        'bundle': rel(bundle_file),
        'evidence_id': data.get('evidence_id'),
        'mission_id': data.get('mission_id'),
        'bead_id': data.get('bead_id'),
        'target_type': data.get('target_type'),
        'validation_result': data.get('validation_result'),
        'closeout_ready': data.get('closeout_ready'),
        'allowed': ok,
        'errors': errors,
    }


def print_result(result: dict[str, Any]) -> None:
    print('# CAT Evidence Validation Result')
    print()
    print(f"Bundle: {result['bundle']}")
    print(f"Evidence: {result['evidence_id']}")
    print(f"Mission: {result['mission_id']}")
    print(f"BEAD: {result.get('bead_id') or 'none'}")
    print(f"Target Type: {result['target_type']}")
    print(f"Validation Result: {result['validation_result']}")
    print(f"Closeout Ready: {result['closeout_ready']}")
    print(f"Allowed: {result['allowed']}")
    if result['errors']:
        print()
        print('## Errors')
        for error in result['errors']:
            print(f'- {error}')


def create_bundle(args: argparse.Namespace) -> Path:
    evidence_id = args.evidence_id or f"EB-{args.mission.replace('MP-', '')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    target_type = 'bead' if args.bead else 'mission'
    artifacts = [
        {
            'path': item,
            'kind': 'artifact',
            'required': True,
            'description': 'Operator-supplied required artifact',
            'validation_result': args.result,
        }
        for item in args.artifact
    ]
    data: dict[str, Any] = {
        'evidence_id': evidence_id,
        'mission_id': args.mission,
        'bead_id': args.bead,
        'target_type': target_type,
        'type': args.type,
        'summary': args.summary,
        'validation_result': args.result,
        'required_artifacts': artifacts,
        'supporting_artifacts': [],
        'metrics': {'required_artifacts': len(artifacts)},
        'created_by': args.created_by,
        'created_at': utc_now(),
        'learning_note': args.learning,
        'closeout_ready': args.result in {'passed', 'skipped'},
    }
    out_dir = ROOT / 'evidence/bundles/generated'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{evidence_id}.yaml'
    write_yaml(out_path, data)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Create and validate CAT evidence bundles.')
    sub = parser.add_subparsers(dest='command', required=True)

    validate = sub.add_parser('validate', help='Validate an evidence bundle.')
    validate.add_argument('--bundle', required=True)
    validate.add_argument('--json', action='store_true')

    create = sub.add_parser('create', help='Create a new evidence bundle.')
    create.add_argument('--mission', required=True)
    create.add_argument('--bead')
    create.add_argument('--evidence-id')
    create.add_argument('--type', default='closeout')
    create.add_argument('--result', choices=['passed', 'failed', 'skipped', 'blocked'], required=True)
    create.add_argument('--summary', required=True)
    create.add_argument('--artifact', action='append', default=[], help='Required artifact path. Repeatable.')
    create.add_argument('--learning', required=True)
    create.add_argument('--created-by', default='Human Owner')

    args = parser.parse_args()

    if args.command == 'create':
        out_path = create_bundle(args)
        print(f'Created {rel(out_path)}')
        return 0

    path = bundle_path(args.bundle)
    ok, errors, data = validate_bundle(path)
    result = summarize_result(ok, errors, data, path)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_result(result)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
