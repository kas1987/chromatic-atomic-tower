#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import ROOT, load_yaml, write_yaml

NEW_MISSION_ID_RE = re.compile(r'^MP-CAT-[SABC][0-9]{3}-[1-4]C[0-9]{2}$')
LEGACY_MISSION_ID_RE = re.compile(r'^MP-CAT-([0-9]{3})$')
NEW_BEAD_ID_RE = re.compile(r'^BEAD-CAT-[SABC][0-9]{3}-[1-4]C[0-9]{2}-[0-9]{2}$')
LEGACY_BEAD_ID_RE = re.compile(r'^BEAD-CAT-[0-9]{3}-[0-9]{3}$')
NEW_WORK_LEGACY_NUMERIC_CUTOFF = 6


def _legacy_mission_number(mission_id: str) -> int | None:
    match = LEGACY_MISSION_ID_RE.match(mission_id)
    if not match:
        return None
    return int(match.group(1))


def _derive_bead_id_from_mission(mission_id: str, seq: str) -> str:
    return mission_id.replace('MP-CAT', 'BEAD-CAT', 1) + f'-{seq}'


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a new CAT BEAD from the BEAD template.')
    parser.add_argument('--id', help='BEAD ID, e.g. BEAD-CAT-S001-4C01-01')
    parser.add_argument('--seq', help='Two-digit sequence for mission-stem bead ID, e.g. 01')
    parser.add_argument('--mission', required=True, help='Mission ID, e.g. MP-CAT-S001-4C01')
    parser.add_argument('--allow-legacy-id', action='store_true', help='Allow grandfathered legacy IDs below cutover.')
    parser.add_argument('--title', required=True)
    parser.add_argument('--out', default='beads/active')
    args = parser.parse_args()

    mission_id = args.mission.strip()
    mission_num = _legacy_mission_number(mission_id)

    if args.id and args.seq:
        parser.error('provide only one of --id or --seq')
    if not args.id and not args.seq:
        parser.error('one of --id or --seq is required')

    if mission_num is not None and mission_num >= NEW_WORK_LEGACY_NUMERIC_CUTOFF:
        parser.error('legacy numeric mission IDs at or above MP-CAT-006 are not allowed; use MP-CAT-A006-4C01 style (tier in [S,A,B,C])')

    if args.seq:
        seq = args.seq.strip()
        if not re.fullmatch(r'[0-9]{2}', seq):
            parser.error('--seq must be a two-digit value, e.g. 01')
        if not NEW_MISSION_ID_RE.match(mission_id):
            parser.error('--seq generation requires a new-format mission id, e.g. MP-CAT-A006-4C01')
        bead_id = _derive_bead_id_from_mission(mission_id, seq)
    else:
        bead_id = args.id.strip()

    mission_is_new = bool(NEW_MISSION_ID_RE.match(mission_id))
    bead_is_new = bool(NEW_BEAD_ID_RE.match(bead_id))
    bead_is_legacy = bool(LEGACY_BEAD_ID_RE.match(bead_id))

    if args.allow_legacy_id:
        if not (mission_is_new or mission_num is not None):
            parser.error('invalid mission id; expected new format or grandfathered legacy format')
        if mission_is_new and not bead_is_new:
            parser.error('new-format mission IDs require new-format bead IDs')
        if mission_num is not None and mission_num < NEW_WORK_LEGACY_NUMERIC_CUTOFF:
            if not (bead_is_new or bead_is_legacy):
                parser.error('invalid bead id; expected new format or grandfathered legacy format')
    else:
        if not mission_is_new:
            parser.error('mission id must use MP-CAT-A006-4C01 style (tier in [S,A,B,C]); use --allow-legacy-id for grandfathered ids')
        if not bead_is_new:
            parser.error('bead id must use BEAD-CAT-S001-4C01-01 style (or use --seq)')

    data = load_yaml(ROOT / 'beads/templates/BEAD_TEMPLATE.yaml')
    data['bead_id'] = bead_id
    data['mission_id'] = mission_id
    data['title'] = args.title
    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in args.title.upper()).strip('_')[:60]
    out_path = ROOT / args.out / f'{bead_id}_{safe_title}.yaml'
    write_yaml(out_path, data)
    print(f'Created {out_path.relative_to(ROOT)}')
    print('Next: edit the BEAD fields, then run python scripts/cat_validate.py --file ' + str(out_path.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
