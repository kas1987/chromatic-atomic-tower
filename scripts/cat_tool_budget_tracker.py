#!/usr/bin/env python3
"""cat_tool_budget_tracker.py — compare actual tool usage against BEAD contract budgets.

Subcommands:
  summarize --bead BEAD_PATH [--actual USAGE_JSON]
      Print per-category usage as % of budget. Emits JSON report.
  check --bead BEAD_PATH [--actual USAGE_JSON]
      Exit 1 if any budget category is exceeded; exit 0 otherwise.

USAGE_JSON format (optional):
  {"search": 1, "read": 5, "write": 3, "execute": 2}

If --actual is omitted, actual usage is treated as 0 (budget check always passes).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

BUDGET_KEYS = ('search', 'read', 'write', 'execute')


def _load_bead(bead_path: str | Path) -> dict:
    p = Path(bead_path)
    try:
        data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    except FileNotFoundError:
        print(f'error: BEAD contract not found: {bead_path}', file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f'error: invalid YAML in BEAD contract: {exc}', file=sys.stderr)
        sys.exit(1)
    return data


def _load_actual(actual_path: str | Path | None) -> dict[str, int]:
    if actual_path is None:
        return {}
    p = Path(actual_path)
    try:
        raw = json.loads(p.read_text(encoding='utf-8'))
    except FileNotFoundError:
        print(f'error: actual usage file not found: {actual_path}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f'error: invalid JSON in actual usage file: {exc}', file=sys.stderr)
        sys.exit(1)
    return {k: int(raw.get(k, 0)) for k in BUDGET_KEYS}


def compute_usage(bead: dict, actual: dict[str, int]) -> dict:
    budget = bead.get('tool_budget') or {}
    bead_id = bead.get('bead_id', 'unknown')
    max_runtime = budget.get('max_runtime_minutes')

    categories: list[dict] = []
    exceeded: list[str] = []

    for key in BUDGET_KEYS:
        limit = budget.get(key)
        used = actual.get(key, 0)
        if limit is None:
            pct = None
            over = False
        else:
            pct = round(used / limit * 100, 1) if limit > 0 else (100.0 if used > 0 else 0.0)
            over = used > limit
        entry = {
            'category': key,
            'used': used,
            'limit': limit,
            'pct': pct,
            'exceeded': over,
        }
        categories.append(entry)
        if over:
            exceeded.append(key)

    return {
        'bead_id': bead_id,
        'max_runtime_minutes': max_runtime,
        'categories': categories,
        'exceeded': exceeded,
        'status': 'exceeded' if exceeded else 'ok',
    }


def cmd_summarize(args: argparse.Namespace) -> int:
    bead = _load_bead(args.bead)
    actual = _load_actual(getattr(args, 'actual', None))
    report = compute_usage(bead, actual)

    if getattr(args, 'json', False):
        print(json.dumps(report, indent=2))
        return 0

    print(f'Tool budget report — {report["bead_id"]}')
    print(f'  Runtime limit: {report["max_runtime_minutes"]} min')
    for cat in report['categories']:
        limit_str = str(cat['limit']) if cat['limit'] is not None else 'unlimited'
        pct_str = f'{cat["pct"]:>5.1f}%' if cat['pct'] is not None else '    n/a'
        flag = ' EXCEEDED' if cat['exceeded'] else ''
        print(f'  {cat["category"]:<8} {cat["used"]:>3}/{limit_str:<10} {pct_str}{flag}')

    if report['exceeded']:
        print(f'\nBudget exceeded in: {", ".join(report["exceeded"])}')
    else:
        print('\nAll budget categories within limits.')

    if getattr(args, 'output', None):
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f'Report written to {args.output}')

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    bead = _load_bead(args.bead)
    actual = _load_actual(getattr(args, 'actual', None))
    report = compute_usage(bead, actual)

    if report['exceeded']:
        print(f'FAIL: budget exceeded in {", ".join(report["exceeded"])} for {report["bead_id"]}', file=sys.stderr)
        return 1

    print(f'OK: all budget categories within limits for {report["bead_id"]}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='CAT tool-budget tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_sum = sub.add_parser('summarize', help='Print per-category usage as %% of budget')
    p_sum.add_argument('--bead', required=True, help='Path to BEAD contract YAML')
    p_sum.add_argument('--actual', default=None, help='Path to actual usage JSON (optional)')
    p_sum.add_argument('--output', default=None, help='Write JSON report to this path')
    p_sum.add_argument('--json', action='store_true', help='Output as JSON')

    p_chk = sub.add_parser('check', help='Exit 1 if any budget category exceeded')
    p_chk.add_argument('--bead', required=True, help='Path to BEAD contract YAML')
    p_chk.add_argument('--actual', default=None, help='Path to actual usage JSON (optional)')

    args = parser.parse_args()
    dispatch = {'summarize': cmd_summarize, 'check': cmd_check}
    return dispatch[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
