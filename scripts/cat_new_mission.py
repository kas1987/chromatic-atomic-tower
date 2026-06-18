#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import ROOT, load_yaml, write_yaml

NEW_MISSION_ID_RE = re.compile(r'^MP-CAT-[SABC][0-9]{3}-[1-4]C[0-9]{2}$')
LEGACY_MISSION_ID_RE = re.compile(r'^MP-CAT-([0-9]{3})$')
EXAMPLE_MISSION_ID_RE = re.compile(r'^MP-CAT-EXAMPLE-[A-Z0-9-]+$')
NEW_WORK_LEGACY_NUMERIC_CUTOFF = 6


def _legacy_mission_number(mission_id: str) -> int | None:
    match = LEGACY_MISSION_ID_RE.match(mission_id)
    if not match:
        return None
    return int(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a new CAT mission from a template.')
    parser.add_argument('--template', required=True, choices=['M1_BASIC', 'M2_INTERMEDIATE', 'M3_COMPLEX', 'M4_ATOMIC'])
    parser.add_argument('--id', required=True, help='Mission ID, e.g. MP-CAT-A006-4C01 (tier in [S,A,B,C])')
    parser.add_argument('--allow-legacy-id', action='store_true', help='Allow grandfathered legacy mission IDs below cutover.')
    parser.add_argument('--title', required=True)
    parser.add_argument('--out', default='missions/backlog')
    args = parser.parse_args()

    mission_id = args.id.strip()
    mission_num = _legacy_mission_number(mission_id)

    if mission_num is not None and mission_num >= NEW_WORK_LEGACY_NUMERIC_CUTOFF:
        parser.error('legacy numeric mission IDs at or above MP-CAT-006 are not allowed; use MP-CAT-A006-4C01 style (tier in [S,A,B,C])')

    if args.allow_legacy_id:
        allowed = bool(
            NEW_MISSION_ID_RE.match(mission_id)
            or EXAMPLE_MISSION_ID_RE.match(mission_id)
            or mission_num is not None
        )
        if not allowed:
            parser.error('invalid mission id; expected MP-CAT-A006-4C01 style (tier in [S,A,B,C]) or a grandfathered legacy id')
    else:
        if not NEW_MISSION_ID_RE.match(mission_id):
            parser.error('mission id must use MP-CAT-A006-4C01 style (tier in [S,A,B,C]); use --allow-legacy-id for grandfathered ids')

    template_path = ROOT / 'missions/templates' / f'{args.template}.yaml'
    data = load_yaml(template_path)
    data['mission_id'] = mission_id
    data['title'] = args.title
    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in args.title.upper()).strip('_')[:60]
    out_path = ROOT / args.out / f'{mission_id}_{safe_title}.yaml'
    write_yaml(out_path, data)
    print(f'Created {out_path.relative_to(ROOT)}')
    print('Next: edit the mission fields, then run python scripts/cat_validate.py --file ' + str(out_path.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
