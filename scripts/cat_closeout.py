#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description='Create a CAT BEAD closeout report. Sprint 000 does not mutate status automatically.')
    parser.add_argument('--bead', required=True)
    parser.add_argument('--result', required=True, choices=['passed', 'failed', 'blocked', 'skipped'])
    parser.add_argument('--summary', required=True)
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out_path = ROOT / 'evidence/reports' / f'{args.bead}_closeout_{ts}.md'
    out_path.write_text(
        f"# CAT Closeout Report\n\n"
        f"BEAD: {args.bead}\n\n"
        f"Result: {args.result}\n\n"
        f"Summary: {args.summary}\n\n"
        f"Created: {ts}\n\n"
        f"## Evidence\n\n- Add evidence links here.\n\n"
        f"## Learning\n\n- Add learning or state that no new learning was found.\n",
        encoding='utf-8',
    )
    print(f'Created {out_path.relative_to(ROOT)}')
    print('Sprint 001 should add automatic state transition mutation after review.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
