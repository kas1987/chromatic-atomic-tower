#!/usr/bin/env python3
"""Read-only cross-file CAT taxonomy and identity drift audit."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cat_validate import taxonomy_patterns
from common import ROOT, load_yaml, rel


MISSION_PATTERNS = (
    'missions/active/*.yaml',
    'missions/backlog/*.yaml',
    'missions/archived/*.yaml',
    'missions/examples/*.yaml',
)
BEAD_PATTERNS = (
    'beads/queued/*.yaml',
    'beads/active/*.yaml',
    'beads/completed/*.yaml',
    'beads/failed/*.yaml',
    'beads/examples/*.yaml',
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    source: str
    consumer: str
    message: str
    observed: Any = None
    expected: Any = None


def _paths(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    return sorted({path for pattern in patterns for path in root.glob(pattern) if path.is_file()})


def _parse_patterns(root: Path) -> tuple[re.Pattern[str], re.Pattern[str]]:
    contract = taxonomy_patterns(root)['contract']
    identity = contract['identity']
    mission = identity['mission']
    bead = identity['bead']
    tokens = mission['tokens']

    def digits(value: object, default: int) -> int:
        match = re.search(r'(\d+)', str(value))
        if match:
            return int(match.group(1))
        return {'one_digits': 1, 'two_digits': 2, 'three_digits': 3}.get(str(value), default)

    repo = re.escape(str(tokens['repo']['value']))
    classes = ''.join(str(value) for value in tokens['class']['values'])
    complexities = ''.join(str(value) for value in tokens['complexity']['values'])
    marker = re.escape(str(tokens['marker']['value']))
    number_digits = digits(tokens['number']['format'], 3)
    order_digits = digits(tokens['order']['format'], 2)
    sequence_digits = digits(bead['sequence']['format'], 2)
    mission_re = re.compile(
        rf'^MP-{repo}-(?P<class>[{classes}])(?P<number>[0-9]{{{number_digits}}})-'
        rf'(?P<complexity>[{complexities}]){marker}(?P<order>[0-9]{{{order_digits}}})$'
    )
    bead_re = re.compile(
        rf'^BEAD-{repo}-(?P<class>[{classes}])(?P<number>[0-9]{{{number_digits}}})-'
        rf'(?P<complexity>[{complexities}]){marker}(?P<order>[0-9]{{{order_digits}}})-'
        rf'(?P<sequence>[0-9]{{{sequence_digits}}})$'
    )
    return mission_re, bead_re


def _finding(
    findings: list[Finding], code: str, severity: str, source: Path, consumer: Path | str,
    message: str, observed: Any = None, expected: Any = None, root: Path = ROOT,
) -> None:
    def relative(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(root.resolve())).replace('\\', '/')
        except ValueError:
            return rel(path).replace('\\', '/')

    consumer_text = relative(consumer) if isinstance(consumer, Path) else str(consumer)
    findings.append(Finding(code, severity, relative(source), consumer_text, message, observed, expected))


def audit_root(root: Path = ROOT) -> dict[str, Any]:
    """Return deterministic audit data without changing repository state."""
    root = root.resolve()
    patterns = taxonomy_patterns(root)
    mission_re, bead_re = _parse_patterns(root)
    mission_paths = _paths(root, MISSION_PATTERNS)
    bead_paths = _paths(root, BEAD_PATTERNS)
    missions: dict[str, tuple[dict[str, Any], Path]] = {}
    beads: dict[str, tuple[dict[str, Any], Path]] = {}
    findings: list[Finding] = []
    compatibility: list[dict[str, str]] = []

    def emit(*args: Any, **kwargs: Any) -> None:
        _finding(*args, root=root, **kwargs)

    for path in mission_paths:
        data = load_yaml(path) or {}
        mission_id = str(data.get('mission_id', '')).strip()
        if not mission_id:
            continue
        if mission_id in missions:
            emit(findings, 'DUPLICATE_MISSION_ID', 'error', path, missions[mission_id][1], 'mission ID has multiple contract sources', mission_id)
        missions[mission_id] = (data, path)
        if mission_re.fullmatch(mission_id):
            complexity = mission_re.fullmatch(mission_id).group('complexity')
            level = str(data.get('level', '')).strip()
            if level and level != f'M{complexity}':
                emit(findings, 'COMPLEXITY_MISMATCH', 'error', path, 'mission identity', f'canonical complexity token disagrees with level: {mission_id} vs {level}', level, f'M{complexity}')
            if data.get('mission_class') and data['mission_class'] != mission_re.fullmatch(mission_id).group('class'):
                emit(findings, 'MISSION_CLASS_MISMATCH', 'error', path, 'mission identity', 'mission_class disagrees with canonical ID class', data.get('mission_class'), mission_re.fullmatch(mission_id).group('class'))
        elif patterns['legacy_mission'].fullmatch(mission_id) or patterns['example_mission'].fullmatch(mission_id):
            compatibility.append({'kind': 'mission', 'id': mission_id, 'source': rel(path), 'reason': 'preserved legacy/example identity'})
        else:
            emit(findings, 'INVALID_MISSION_ID', 'error', path, 'taxonomy contract', 'mission ID is not canonical or preserved compatibility form', mission_id)
        priority = data.get('priority')
        if not isinstance(priority, int) or priority not in {1, 2, 3, 4, 5}:
            emit(findings, 'INVALID_PRIORITY', 'error', path, 'taxonomy contract', 'priority must be an integer from 1 through 5', priority, [1, 2, 3, 4, 5])
    for path in bead_paths:
        data = load_yaml(path) or {}
        bead_id = str(data.get('bead_id', '')).strip()
        mission_id = str(data.get('mission_id', '')).strip()
        if not bead_id:
            continue
        if bead_id in beads:
            emit(findings, 'DUPLICATE_BEAD_ID', 'error', path, beads[bead_id][1], 'BEAD ID has multiple contract sources', bead_id)
        beads[bead_id] = (data, path)
        match = bead_re.fullmatch(bead_id)
        if match:
            expected_stem = f"MP-CAT-{match.group('class')}{match.group('number')}-{match.group('complexity')}C{match.group('order')}"
            if mission_id != expected_stem:
                emit(findings, 'BEAD_STEM_MISMATCH', 'error', path, 'mission_id', 'canonical BEAD stem does not match mission_id', mission_id, expected_stem)
        elif patterns['legacy_bead'].fullmatch(bead_id) or any(pattern.fullmatch(bead_id) for pattern in patterns['example_bead']):
            compatibility.append({'kind': 'bead', 'id': bead_id, 'source': rel(path), 'reason': 'preserved legacy/example identity'})
        else:
            emit(findings, 'INVALID_BEAD_ID', 'error', path, 'taxonomy contract', 'BEAD ID is not canonical or preserved compatibility form', bead_id)
        if mission_id not in missions:
            emit(findings, 'MISSING_PARENT_MISSION', 'error', path, 'mission contract', 'BEAD parent mission is not present', mission_id)
        priority = data.get('priority')
        if not isinstance(priority, int) or priority not in {1, 2, 3, 4, 5}:
            emit(findings, 'INVALID_PRIORITY', 'error', path, 'taxonomy contract', 'priority must be an integer from 1 through 5', priority, [1, 2, 3, 4, 5])
        parent = missions.get(mission_id, ({}, path))[0]
        if data.get('complexity') and parent.get('level') and data['complexity'] != parent['level']:
            emit(findings, 'BEAD_COMPLEXITY_MISMATCH', 'error', path, 'parent mission', 'explicit BEAD complexity disagrees with parent mission level', data.get('complexity'), parent.get('level'))
        for validation in data.get('validation', []) or []:
            evidence_path = validation.get('evidence_path') if isinstance(validation, dict) else None
            if not evidence_path:
                continue
            evidence_file = root / evidence_path
            if not evidence_file.exists():
                status = str(data.get('status', '')).strip()
                severity = 'expected' if status not in {'completed', 'failed', 'archived'} else 'error'
                emit(findings, 'MISSING_EVIDENCE_PATH', severity, path, evidence_path, 'validation evidence path does not exist', evidence_path, 'existing evidence artifact')

    for mission_id, (data, path) in missions.items():
        for dependency in data.get('dependencies', []) or []:
            if isinstance(dependency, str) and dependency.startswith('MP-') and dependency not in missions and dependency != mission_id:
                emit(findings, 'MISSING_MISSION_DEPENDENCY', 'error', path, 'mission dependency graph', 'mission dependency is not present in a mission contract', dependency)

    for bead_id, (data, path) in beads.items():
        for dependency in data.get('dependencies', []) or []:
            if isinstance(dependency, str) and dependency.startswith(('MP-', 'BEAD-')) and dependency not in beads and dependency not in missions:
                emit(findings, 'MISSING_BEAD_DEPENDENCY', 'error', path, 'dependency graph', 'BEAD dependency is not present in a mission or BEAD contract', dependency)

    registry_path = root / 'missions/registry/MISSION_REGISTRY.yaml'
    if registry_path.exists():
        registry = load_yaml(registry_path) or {}
        for entry in registry.get('missions', []) or []:
            mission_id = entry.get('mission_id')
            path_value = entry.get('path')
            if not mission_id or not path_value:
                continue
            target = root / path_value
            if not target.exists():
                emit(findings, 'REGISTRY_PATH_MISSING', 'error', registry_path, path_value, 'registry mission path does not exist', path_value)
            elif mission_id not in missions or missions[mission_id][1] != target:
                emit(findings, 'REGISTRY_CONTRACT_ASYMMETRY', 'error', registry_path, path_value, 'registry path does not resolve to the same mission identity', mission_id, rel(target))

    tower_path = root / 'state/TOWER_STATE.yaml'
    if registry_path.exists() and tower_path.exists():
        registry = load_yaml(registry_path) or {}
        tower = load_yaml(tower_path) or {}
        for field in ('active_mission_id', 'active_bead_id'):
            if registry.get(field) != tower.get(field):
                emit(findings, 'POINTER_ASYMMETRY', 'error', registry_path, tower_path, f'{field} differs between registry and tower', registry.get(field), tower.get(field))

    findings.sort(key=lambda item: (item.severity, item.code, item.source, item.consumer, item.message))
    return {
        'contract_id': patterns['contract'].get('contract_id'),
        'contract_version': patterns['contract'].get('version'),
        'root': str(root),
        'source_files': len(mission_paths) + len(bead_paths),
        'mission_contracts': len(missions),
        'bead_contracts': len(beads),
        'findings': [asdict(item) for item in findings],
        'compatibility_exceptions': sorted(compatibility, key=lambda item: (item['kind'], item['id'], item['source'])),
        'summary': {
            'errors': sum(item.severity == 'error' for item in findings),
            'expected_pending': sum(item.severity == 'expected' for item in findings),
            'compatibility_exceptions': len(compatibility),
            'status': 'FAIL' if any(item.severity == 'error' for item in findings) else 'PASS',
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Run a read-only CAT taxonomy drift audit.')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--json', action='store_true', help='Emit deterministic JSON.')
    parser.add_argument('--json-out', type=Path, help='Persist deterministic JSON evidence at an explicit path.')
    args = parser.parse_args()
    result = audit_root(args.root)
    if args.json_out:
        output = args.json_out if args.json_out.is_absolute() else args.root / args.json_out
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"CAT taxonomy audit: {result['summary']['status']}")
        print(f"Errors: {result['summary']['errors']}; expected pending: {result['summary']['expected_pending']}; compatibility: {result['summary']['compatibility_exceptions']}")
        for finding in result['findings']:
            print(f"{finding['severity'].upper()} [{finding['code']}] {finding['source']} -> {finding['consumer']}: {finding['message']}")
    return 1 if result['summary']['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
