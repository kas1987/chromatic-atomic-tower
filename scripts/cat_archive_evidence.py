#!/usr/bin/env python3
"""Archive old evidence to evidence/archive/YYYY/QN/ by retention policy."""

import argparse
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from common import ROOT, load_yaml

EVIDENCE_ROOT = ROOT / 'evidence'
ARCHIVE_ROOT = EVIDENCE_ROOT / 'archive'
LOGS_DIR = EVIDENCE_ROOT / 'logs'

# Paths that should NEVER be archived
EXEMPT_PATHS = {
    'agents/scorecards/',
    'learnings/',
    'evidence/gate_results/',
    'evidence/bundles/',
}

# Evidence directories that are eligible for archival
ELIGIBLE_DIRS = {
    'evidence/ci/',
    'evidence/logs/',
    'evidence/diffs/',
    'evidence/manual/',
    'evidence/scorecard/',  # Some records archived, others exempt
}


def classify_eligibility(file_path: str) -> str:
    """Classify if a file is eligible, exempted, or unknown."""
    for exempt in EXEMPT_PATHS:
        if exempt in file_path:
            return 'exempted'
    for eligible in ELIGIBLE_DIRS:
        if eligible in file_path:
            return 'eligible'
    return 'unknown'


def get_file_age_days(file_path: Path) -> float:
    """Get age of file in days."""
    if not file_path.exists():
        return 0
    mtime = file_path.stat().st_mtime
    age_seconds = datetime.now().timestamp() - mtime
    return age_seconds / 86400


def get_quarter(date: datetime) -> str:
    """Get quarter (Q1-Q4) for a date."""
    month = date.month
    if 1 <= month <= 3:
        return 'Q1'
    elif 4 <= month <= 6:
        return 'Q2'
    elif 7 <= month <= 9:
        return 'Q3'
    else:
        return 'Q4'


def archive_destination(file_path: Path) -> Path:
    """Calculate destination path in archive/YYYY/QN/."""
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    year = mtime.year
    quarter = get_quarter(mtime)
    filename = file_path.name
    dest = ARCHIVE_ROOT / str(year) / quarter / filename
    return dest


def create_archive_record(
    source_path: str,
    destination_path: str | None,
    file_size_bytes: int,
    event: str,
    eligibility: str,
    reason: str | None = None,
    git_commit_sha: str | None = None,
    age_days: float = 0,
    batch_id: str = '',
) -> dict:
    """Create an archive record conforming to schemas/archive.schema.json."""
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'source_path': source_path,
        'destination_path': destination_path,
        'file_size_bytes': file_size_bytes,
        'event': event,
        'eligibility': eligibility,
        **(
            {'reason': reason}
            if reason
            else {}
        ),
        'git_commit_sha': git_commit_sha,
        'age_days': age_days,
        'archival_batch_id': batch_id,
    }


def cmd_status(older_than_days: int = 90) -> None:
    """Report evidence older than threshold."""
    eligible = []
    for evidence_file in EVIDENCE_ROOT.rglob('*'):
        if not evidence_file.is_file():
            continue
        rel_path = str(evidence_file.relative_to(ROOT))
        if any(exempt in rel_path for exempt in EXEMPT_PATHS):
            continue
        age = get_file_age_days(evidence_file)
        if age >= older_than_days:
            eligible.append(
                {
                    'path': rel_path,
                    'age_days': age,
                    'size_bytes': evidence_file.stat().st_size,
                }
            )

    if not eligible:
        print(f'No evidence older than {older_than_days} days.')
        return

    total_size = sum(e['size_bytes'] for e in eligible)
    print(f'Found {len(eligible)} evidence file(s) eligible for archival ({total_size} bytes)')
    for e in eligible[:10]:
        print(
            f"  {e['path']:<60} {e['age_days']:>6.1f}d {e['size_bytes']:>10} B"
        )
    if len(eligible) > 10:
        print(f'  ... and {len(eligible) - 10} more')


def cmd_dry_run(older_than_days: int = 90, batch_id: str = '') -> list[dict]:
    """Show what would be archived without executing."""
    records = []
    for evidence_file in EVIDENCE_ROOT.rglob('*'):
        if not evidence_file.is_file():
            continue
        rel_path = str(evidence_file.relative_to(ROOT))
        eligibility = classify_eligibility(rel_path)
        age = get_file_age_days(evidence_file)
        size = evidence_file.stat().st_size

        if eligibility == 'exempted':
            record = create_archive_record(
                source_path=rel_path,
                destination_path=None,
                file_size_bytes=size,
                event='skipped',
                eligibility='exempted',
                reason='Exempted by policy (scorecard/learnings/gate results)',
                age_days=age,
                batch_id=batch_id,
            )
            records.append(record)
        elif eligibility == 'eligible' and age >= older_than_days:
            dest = archive_destination(evidence_file)
            dest_rel = str(dest.relative_to(ROOT))
            record = create_archive_record(
                source_path=rel_path,
                destination_path=dest_rel,
                file_size_bytes=size,
                event='archived',
                eligibility='eligible',
                age_days=age,
                batch_id=batch_id,
            )
            records.append(record)

    print(f'Dry-run: would archive {len([r for r in records if r["event"] == "archived"])} file(s)')
    for r in records:
        if r['event'] == 'archived':
            print(f"  {r['source_path']:<50} -> {Path(r['destination_path']).name}")
    return records


def cmd_run(older_than_days: int = 90, batch_id: str = '') -> list[dict]:
    """Execute archival: move files and log records."""
    records = cmd_dry_run(older_than_days, batch_id)

    for record in records:
        if record['event'] != 'archived':
            continue
        source = ROOT / record['source_path']
        dest = ROOT / record['destination_path']

        if not source.exists():
            record['event'] = 'failed'
            record['reason'] = 'Source file not found'
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            source.rename(dest)
            record['git_commit_sha'] = None  # Filled in by git later if needed
        except Exception as e:
            record['event'] = 'failed'
            record['reason'] = str(e)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"archival_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.jsonl"
    with open(log_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    print(f'Archived {len([r for r in records if r["event"] == "archived"])} file(s)')
    print(f'Log written to {log_file.relative_to(ROOT)}')
    return records


def main():
    parser = argparse.ArgumentParser(description='Archive old evidence by retention policy')
    parser.add_argument(
        '--older-than',
        type=int,
        default=90,
        help='Archive evidence older than N days (default 90)',
    )
    parser.add_argument(
        '--batch-id',
        type=str,
        default=datetime.now().strftime('batch_%Y_%m_%d_%H%M%S'),
        help='Batch ID for grouping archival operations',
    )

    subparsers = parser.add_subparsers(dest='command', help='Archival subcommand')
    subparsers.add_parser('status', help='Report evidence eligible for archival')
    subparsers.add_parser('dry-run', help='Show proposed archival without executing')
    subparsers.add_parser('run', help='Execute archival')

    args = parser.parse_args()

    if args.command == 'status':
        cmd_status(args.older_than)
    elif args.command == 'dry-run':
        cmd_dry_run(args.older_than, args.batch_id)
    elif args.command == 'run':
        cmd_run(args.older_than, args.batch_id)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
