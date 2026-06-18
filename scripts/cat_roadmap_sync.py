#!/usr/bin/env python3
"""Check CAT_ROADMAP.md for canonical Sprint 009 sequence."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT

TERMS = [
    'Sprint 000',
    'Core Foundation',
    'Sprint 001',
    'State Transition Engine',
    'Sprint 002',
    'Evidence Gate',
    'Sprint 003',
    'CI Governance',
    'Sprint 004',
    'V2 Alignment',
    'Sprint 005',
    'Multi-Model Coding Harness',
    'Sprint 006',
    'Harness Engineering',
    'Sprint 007',
    'LOGHOUSE',
    'Sprint 008',
    'State Alignment',
    'Sprint 009',
    'Repo Alignment and Mission Packet Reconciliation',
    'GitHub Bridge + PR Governance',
    'Agent Scorecard Automation',
    'CAT Portable Project Adapter',
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--path', default='CAT_ROADMAP.md')
    args = ap.parse_args()
    text = (ROOT / args.path).read_text(encoding='utf-8')
    missing = [t for t in TERMS if t not in text]
    if missing:
        print('Roadmap sync check failed:')
        for m in missing:
            print(f'- missing {m}')
        return 1
    print('Roadmap sync check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
