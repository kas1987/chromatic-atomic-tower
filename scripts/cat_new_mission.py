#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_yaml, write_yaml


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a new CAT mission from a template.')
    parser.add_argument('--template', required=True, choices=['M1_BASIC', 'M2_INTERMEDIATE', 'M3_COMPLEX', 'M4_ATOMIC'])
    parser.add_argument('--id', required=True, help='Mission ID, e.g. MP-CAT-001')
    parser.add_argument('--title', required=True)
    parser.add_argument('--out', default='missions/backlog')
    args = parser.parse_args()

    template_path = ROOT / 'missions/templates' / f'{args.template}.yaml'
    data = load_yaml(template_path)
    data['mission_id'] = args.id
    data['title'] = args.title
    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in args.title.upper()).strip('_')[:60]
    out_path = ROOT / args.out / f'{args.id}_{safe_title}.yaml'
    write_yaml(out_path, data)
    print(f'Created {out_path.relative_to(ROOT)}')
    print('Next: edit the mission fields, then run python scripts/cat_validate.py --file ' + str(out_path.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
