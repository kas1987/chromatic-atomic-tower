#!/usr/bin/env python3
"""Validate MP-CAT-A006-4C01 Harness Engineering alignment contracts.

Checks that the audit-methodology layer is present and internally consistent:
required files exist, all eight beads exist and carry CAT-native keys, the
mission references every bead, the assertion gate set is complete, the folded
complexity routing policy is well-formed, and the Mermaid docs are fenced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

MISSION_PATH = 'missions/active/MP-CAT-A006-4C01_HARNESS_ENGINEERING_ALIGNMENT.yaml'

REQUIRED_FILES = [
    MISSION_PATH,
    'gates/assertion_gates.yaml',
    'agents/skills/SKILL_REGISTRY.yaml',
    'agents/model_routes.yaml',
    'docs/architecture/HARNESS_ENGINEERING_AUDIT_ALIGNMENT.md',
    'docs/architecture/CAT_MISSION_PIPELINE_MERMAID.md',
    'evidence/templates/ASSERTION_EVIDENCE_MAP.yaml',
    '.github/workflows/cat-governance-ci.yml',
    '.github/workflows/cat-cd-promotion.yml',
]

REQUIRED_BEADS = [f'BEAD-CAT-A006-4C01-0{i}' for i in range(1, 9)]
REQUIRED_GATES = {
    'completeness_gate',
    'substantive_validation_gate',
    'control_validation_gate',
    'evidence_sufficiency_gate',
    'promotion_gate',
}
# CAT-native BEAD keys (replaces the pack's evidence_required with required_output).
REQUIRED_BEAD_KEYS = [
    'mission_id', 'allowed_paths', 'forbidden_paths',
    'validation', 'required_output', 'definition_of_done',
]


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

    if yaml is None:
        errors.append('PyYAML is required for YAML validation')
    else:
        for path in (
            list((root / 'gates').glob('*.yaml'))
            + list((root / 'agents').glob('**/*.yaml'))
            + list((root / 'missions').glob('**/*.yaml'))
            + list((root / 'beads').glob('**/*.yaml'))
        ):
            try:
                load_structured(path)
            except Exception as exc:
                errors.append(f'parse failure: {path.relative_to(root)}: {exc}')

    mission_path = root / MISSION_PATH
    if mission_path.exists() and yaml is not None:
        mission = load_structured(mission_path) or {}
        # CAT-native missions list beads as objects with a bead_id key.
        mission_beads = {
            (b.get('bead_id') if isinstance(b, dict) else b)
            for b in mission.get('beads', [])
        }
        missing = [b for b in REQUIRED_BEADS if b not in mission_beads]
        if missing:
            errors.append(f'mission missing BEAD references: {missing}')

    for bead_id in REQUIRED_BEADS:
        matches = list((root / 'beads/active').glob(f'{bead_id}*.yaml'))
        if not matches:
            errors.append(f'missing active BEAD file for {bead_id}')
        for match in matches:
            bead = load_structured(match) if yaml is not None else {}
            for key in REQUIRED_BEAD_KEYS:
                if key not in bead:
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
