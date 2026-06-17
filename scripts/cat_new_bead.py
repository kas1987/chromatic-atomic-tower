#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, load_yaml, write_yaml


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a new CAT BEAD from the BEAD template.')
    parser.add_argument('--id', required=True, help='BEAD ID, e.g. BEAD-CAT-001-001')
    parser.add_argument('--mission', required=True, help='Mission ID, e.g. MP-CAT-001')
    parser.add_argument('--title', required=True)
    parser.add_argument('--out', default='beads/active')
    args = parser.parse_args()

    data = load_yaml(ROOT / 'beads/templates/BEAD_TEMPLATE.yaml')
    data['bead_id'] = args.id
    data['mission_id'] = args.mission
    data['title'] = args.title
    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in args.title.upper()).strip('_')[:60]
    out_path = ROOT / args.out / f'{args.id}_{safe_title}.yaml'
    write_yaml(out_path, data)
    print(f'Created {out_path.relative_to(ROOT)}')
    print('Next: edit the BEAD fields, then run python scripts/cat_validate.py --file ' + str(out_path.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
