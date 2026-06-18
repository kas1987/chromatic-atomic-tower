#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

WEIGHTS = {
    'completeness_score': 0.20,
    'substantive_validation_score': 0.25,
    'control_validation_score': 0.20,
    'evidence_sufficiency_score': 0.15,
    'routing_score': 0.10,
    'exception_disclosure_score': 0.10,
}


def decision(score: float) -> str:
    if score >= 90:
        return 'auto_proceed'
    if score >= 70:
        return 'proceed_with_review'
    if score >= 50:
        return 'self_heal'
    return 'escalate_or_block'


def main() -> int:
    parser = argparse.ArgumentParser(description='Score CAT confidence from gate components.')
    parser.add_argument('--root', default='.', help='Repository root')
    parser.add_argument('--mission', default='MP-CAT-A006-4C01')
    parser.add_argument('--scores', help='Optional JSON object with score components')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.scores:
        components = json.loads(args.scores)
    elif args.dry_run:
        # In dry-run mode a placeholder is acceptable for local testing.
        components = {key: 90 for key in WEIGHTS}
    else:
        root = Path(args.root)
        report_path = root / 'evidence' / 'reports' / f'{args.mission}_validation_report.json'
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding='utf-8'))
            report_status = report.get('status', '')
            if report_status == 'draft':
                print(
                    f'ERROR: validation report is still in draft state: {report_path}. '
                    'Update status to "final" with authoritative gate scores before promotion.',
                    flush=True,
                )
                return 1
            components = report.get('gate_scores', {})
            if not components:
                print(f'ERROR: validation report exists but contains no gate_scores: {report_path}', flush=True)
                return 1
        else:
            print(
                f'ERROR: --scores not provided and no validation report found at {report_path}. '
                'Run the harness alignment validator first or pass --scores explicitly.',
                flush=True,
            )
            return 1

    score = sum(float(components.get(key, 0)) * weight for key, weight in WEIGHTS.items())
    result = {
        'mission_id': args.mission,
        'confidence_score': round(score, 2),
        'decision': decision(score),
        'components': components,
        'weights': WEIGHTS,
    }
    print(json.dumps(result, indent=2))

    if not args.dry_run:
        out = Path(args.root) / 'evidence' / 'reports' / f'{args.mission}_confidence_score.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
