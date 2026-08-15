#!/usr/bin/env python3
"""Create an official Beads issue; CAT no longer creates YAML task ledgers."""
from __future__ import annotations

import argparse
import json

from cat_beads import BeadsCommandError, run_bd


def main() -> int:
    parser = argparse.ArgumentParser(description='Create an official CAT Bead with bd.')
    parser.add_argument('--mission', required=True, help='CAT mission ID carried in Wisker metadata')
    parser.add_argument('--title', required=True)
    parser.add_argument('--description', required=True, help='Include CAT_WISKER_JSON metadata for dispatchable work')
    parser.add_argument('--priority', type=int, default=2)
    args = parser.parse_args()
    description = args.description
    if 'CAT_WISKER_JSON:' not in description:
        description = f'{description}\nCAT_WISKER_JSON: {json.dumps({"mission_id": args.mission})}'
        print('Created a Bead without a complete Wisker contract; GO will fail closed until metadata is completed.')
    try:
        issue = run_bd([
            'create', '--title', args.title, '--description', description,
            '--priority', str(args.priority), '--type', 'task', '--json',
        ])
    except BeadsCommandError as exc:
        print(f'official Beads create failed: {exc}')
        return 1
    print(json.dumps(issue, indent=2) if issue is not None else 'official Bead created')
    print('Next: run bd prime, then python scripts/cat_resolve_go.py --check-schema')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
