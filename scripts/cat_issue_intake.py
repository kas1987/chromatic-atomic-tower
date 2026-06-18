#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


def slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_') or 'draft_mission'


def safe_mission_id(mission_id: str) -> str:
    """Strip path separators and dots so mission_id cannot escape output_dir."""
    return re.sub(r'[^A-Za-z0-9_\-]', '_', mission_id) or 'MP-CAT-DRAFT'


def scaffold(issue_json: str | Path, output_dir: str | Path) -> Path:
    data = json.loads(Path(issue_json).read_text(encoding='utf-8'))
    title = data.get('title', 'Untitled Mission Request')
    mission_id = safe_mission_id(data.get('mission_id', 'MP-CAT-DRAFT'))
    body = data.get('body', '')
    level = data.get('level', 'M2')
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    content = {
        'mission_id': mission_id,
        'title': title,
        'level': level,
        'status': 'draft',
        'source': 'github_issue_intake',
        'objective': body or title,
        'allowed_paths': data.get('allowed_paths') or [],
        'forbidden_paths': ['.env', '.env.*', 'secrets/**', 'credentials/**'],
        'definition_of_done': data.get('definition_of_done') or ['Draft reviewed by Orchestrator'],
    }
    path = out / f'{mission_id}_{slugify(title)}.yaml'
    if not path.resolve().is_relative_to(out):
        raise ValueError(f'Resolved output path escapes output_dir: {path}')
    path.write_text(yaml.safe_dump(content, sort_keys=False), encoding='utf-8')
    print(f'Mission candidate written: {path}')
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description='Scaffold CAT mission candidate from issue JSON.')
    ap.add_argument('--issue-json', required=True)
    ap.add_argument('--output-dir', default='missions/intake')
    args = ap.parse_args()
    scaffold(args.issue_json, args.output_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
