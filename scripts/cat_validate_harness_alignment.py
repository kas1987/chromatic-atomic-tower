#!/usr/bin/env python3
"""Validate MP-CAT-A006-4C01 Harness Engineering alignment contracts.

Checks that the audit-methodology layer is present and internally consistent.
Official Beads own task records; this gate checks the Wisker contract surface.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

MISSION_CANDIDATES = [
    'missions/active/MP-CAT-A006-4C01_HARNESS_ENGINEERING_ALIGNMENT.yaml',
    'missions/archived/MP-CAT-A006-4C01_HARNESS_ENGINEERING_ALIGNMENT.yaml',
]
WISKER_SEARCH_DIRS = ['wiskers/packets', 'wiskers/examples']

REQUIRED_FILES = [
    'gates/assertion_gates.yaml',
    'agents/skills/SKILL_REGISTRY.yaml',
    'agents/model_routes.yaml',
    'docs/architecture/HARNESS_ENGINEERING_AUDIT_ALIGNMENT.md',
    'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md',
    'evidence/templates/ASSERTION_EVIDENCE_MAP.yaml',
    '.github/workflows/cat-governance-ci.yml',
    '.github/workflows/cat-cd-promotion.yml',
]

REQUIRED_WISKERS = ['WISKER-EXAMPLE-001']
REQUIRED_GATES = {
    'completeness_gate',
    'substantive_validation_gate',
    'control_validation_gate',
    'evidence_sufficiency_gate',
    'promotion_gate',
}
REQUIRED_WISKER_KEYS = [
    'wisker_id', 'bd_id', 'source_bead_digest', 'source_commit_sha',
    'mission_id', 'allowed_paths', 'forbidden_paths',
    'validation', 'required_output', 'definition_of_done',
]


def _resolve_mission_path(root: Path) -> str | None:
    for rel in MISSION_CANDIDATES:
        if (root / rel).exists():
            return rel
    return None


def _find_wisker_files(root: Path, wisker_id: str) -> list[Path]:
    matches: list[Path] = []
    for base in WISKER_SEARCH_DIRS:
        matches.extend(sorted((root / base).glob(f'{wisker_id}*.yaml')))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in matches:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def load_structured(path: Path):
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.json':
        return json.loads(text)
    if path.suffix in {'.yaml', '.yml'}:
        if yaml is None:
            raise RuntimeError('PyYAML is required for YAML validation')
        return yaml.safe_load(text)
    return text


def validate(root: Path) -> tuple[int, list[str]]:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f'missing required file: {rel}')

    mission_rel = _resolve_mission_path(root)
    if not mission_rel:
        errors.append(f'missing mission contract: {" or ".join(MISSION_CANDIDATES)}')

    if yaml is None:
        errors.append('PyYAML is required for YAML validation')
    else:
        for path in (
            list((root / 'gates').glob('*.yaml'))
            + list((root / 'agents').glob('**/*.yaml'))
            + list((root / 'missions').glob('**/*.yaml'))
            + list((root / 'wiskers').glob('**/*.yaml'))
        ):
            try:
                load_structured(path)
            except Exception as exc:
                errors.append(f'parse failure: {path.relative_to(root)}: {exc}')

    mission_path = root / mission_rel if mission_rel else None
    if mission_path and mission_path.exists() and yaml is not None:
        mission = load_structured(mission_path) or {}
    for wisker_id in REQUIRED_WISKERS:
        matches = _find_wisker_files(root, wisker_id)
        if not matches:
            errors.append(f'missing Wisker packet for {wisker_id} (searched {", ".join(WISKER_SEARCH_DIRS)})')
        for match in matches:
            wisker = load_structured(match) if yaml is not None else {}
            for key in REQUIRED_WISKER_KEYS:
                if key not in wisker:
                    errors.append(f'{match.relative_to(root)} missing key: {key}')

    gates_path = root / 'gates/assertion_gates.yaml'
    if gates_path.exists() and yaml is not None:
        gates_doc = load_structured(gates_path) or {}
        gate_ids = {g.get('gate_id') for g in gates_doc.get('gates', [])}
        missing = sorted(REQUIRED_GATES - gate_ids)
        if missing:
            errors.append(f'assertion_gates.yaml missing gates: {missing}')

    # Complexity routing is folded into agents/model_routes.yaml under complexity_routing.
    routing_path = root / 'agents/model_routes.yaml'
    if routing_path.exists() and yaml is not None:
        routes = load_structured(routing_path) or {}
        policy = routes.get('complexity_routing', {})
        if not policy:
            errors.append('agents/model_routes.yaml missing complexity_routing block')
        if len(policy.get('default_routes', [])) < 4:
            errors.append('complexity_routing should define at least four default routes')
        if not policy.get('fallback_rules'):
            errors.append('complexity_routing missing fallback rules')

    docs = [
        root / 'docs/architecture/HARNESS_ENGINEERING_AUDIT_ALIGNMENT.md',
        root / 'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md',
    ]
    for doc in docs:
        if doc.exists() and '```mermaid' not in doc.read_text(encoding='utf-8'):
            errors.append(f'{doc.relative_to(root)} has no Mermaid diagram')

    return (1 if errors else 0), errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate MP-CAT-A006-4C01 Harness alignment contracts.')
    parser.add_argument('--root', default='.', help='Repository root')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    code, errors = validate(root)
    if errors:
        print('CAT Harness alignment validation failed:')
        for error in errors:
            print(f' - {error}')
        return code
    print('CAT Harness alignment validation passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
