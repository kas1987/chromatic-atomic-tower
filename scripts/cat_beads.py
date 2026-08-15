#!/usr/bin/env python3
"""Small, fail-closed adapter between CAT and the official ``bd`` CLI."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any

from common import ROOT


class BeadsCommandError(RuntimeError):
    """Raised when official Beads cannot be queried safely."""


def _candidate_commands() -> list[list[str]]:
    override = os.environ.get('CAT_BD_COMMAND', '').strip()
    candidates: list[list[str]] = []
    if override:
        parts = shlex.split(override, posix=os.name != 'nt')
        if parts:
            executable = shutil.which(parts[0])
            if not executable and os.name == 'nt' and not Path(parts[0]).suffix:
                executable = shutil.which(f'{parts[0]}.cmd')
            if executable:
                parts[0] = executable
            candidates.append(parts)
    for name in ('bd.cmd', 'bd'):
        resolved = shutil.which(name)
        if resolved:
            candidates.append([resolved])
    # Deduplicate while preserving preference order.
    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for item in candidates:
        key = tuple(item)
        if item and key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def resolve_bd_command() -> list[str]:
    for command in _candidate_commands():
        try:
            probe = subprocess.run(
                command + ['--version'], capture_output=True, text=True,
                cwd=ROOT, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        output = f'{probe.stdout}\n{probe.stderr}'.lower()
        if probe.returncode == 0 and 'bd version' in output:
            return command
    raise BeadsCommandError(
        'official bd CLI not found or failed --version; install Beads or set CAT_BD_COMMAND'
    )


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env['BEADS_DIR'] = str(Path(env.get('CAT_BEADS_DIR', ROOT / '.beads')).resolve())
    return env


def run_bd(args: list[str], *, timeout: int = 30) -> Any:
    command = resolve_bd_command()
    try:
        result = subprocess.run(
            command + args, cwd=ROOT, env=_env(), capture_output=True,
            text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BeadsCommandError(f'bd {" ".join(args)} failed to start: {exc}') from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise BeadsCommandError(f'bd {" ".join(args)} failed ({result.returncode}): {detail}')
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BeadsCommandError(
            f'bd {" ".join(args)} returned malformed JSON: {exc}'
        ) from exc


def ready_beads() -> list[dict[str, Any]]:
    payload = run_bd(['ready', '--json'])
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get('issues', payload.get('results', payload.get('items')))
    else:
        items = None
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise BeadsCommandError('bd ready --json returned no valid issue list')
    return items


def show_bead(bead_id: str) -> dict[str, Any]:
    payload = run_bd(['show', bead_id, '--json'])
    if isinstance(payload, list):
        if len(payload) != 1 or not isinstance(payload[0], dict):
            raise BeadsCommandError(f'bd show {bead_id} returned an unexpected result')
        return payload[0]
    if isinstance(payload, dict):
        issue = payload.get('issue', payload)
        if isinstance(issue, dict):
            return issue
    raise BeadsCommandError(f'bd show {bead_id} returned no issue object')


def claim_bead(bead_id: str) -> dict[str, Any]:
    payload = run_bd(['update', bead_id, '--claim', '--json'])
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        issue = payload.get('issue', payload)
        if isinstance(issue, dict):
            return issue
    # Some supported bd versions return no JSON for a successful mutation.
    return show_bead(bead_id)


def close_bead(bead_id: str, reason: str) -> dict[str, Any]:
    payload = run_bd(['close', bead_id, '--reason', reason, '--json'])
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        issue = payload.get('issue', payload)
        if isinstance(issue, dict):
            return issue
    return show_bead(bead_id)


def _stable_payload(issue: dict[str, Any]) -> dict[str, Any]:
    """Remove mutable bookkeeping so claiming does not change a Wisker scope."""
    volatile = {
        'status', 'updated_at', 'closed_at', 'started_at', 'lease_expires_at',
        'heartbeat_at', 'assignee', 'owner', 'revision', 'dependency_count',
        'dependent_count', 'comment_count',
    }
    return {key: value for key, value in issue.items() if key not in volatile}


def bead_digest(issue: dict[str, Any]) -> str:
    encoded = json.dumps(_stable_payload(issue), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return sha256(encoded.encode('utf-8')).hexdigest()


def selection_key(issue: dict[str, Any]) -> tuple[int, str, str]:
    try:
        priority = int(issue.get('priority', 5))
    except (TypeError, ValueError):
        priority = 5
    return priority, str(issue.get('created_at', '9999-99-99T99:99:99Z')), str(issue.get('id', ''))


def select_ready(items: list[dict[str, Any]], *, mission_id: str | None = None) -> dict[str, Any] | None:
    candidates = []
    for item in items:
        if not item.get('id'):
            continue
        metadata = wisker_metadata(item)
        if mission_id and metadata.get('mission_id') != mission_id:
            continue
        candidates.append(item)
    return sorted(candidates, key=selection_key)[0] if candidates else None


def wisker_metadata(issue: dict[str, Any]) -> dict[str, Any]:
    for key in ('wisker', 'metadata', 'cat_metadata'):
        value = issue.get(key)
        if isinstance(value, dict):
            return value.get('wisker', value) if isinstance(value.get('wisker', value), dict) else value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed.get('wisker', parsed) if isinstance(parsed.get('wisker', parsed), dict) else parsed
    description = str(issue.get('description', ''))
    marker = 'CAT_WISKER_JSON:'
    if marker in description:
        raw = description.split(marker, 1)[1].splitlines()[0].strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def build_wisker(issue: dict[str, Any], source_commit_sha: str) -> dict[str, Any]:
    metadata = wisker_metadata(issue)
    required = (
        'mission_id', 'objective', 'agent_role', 'autonomy_level', 'confidence',
        'risk', 'allowed_paths', 'forbidden_paths', 'tool_budget',
        'definition_of_done', 'validation', 'stop_conditions', 'required_output',
    )
    missing = [key for key in required if key not in metadata]
    if missing:
        raise BeadsCommandError(
            f'Bead {issue.get("id", "<unknown>")} lacks Wisker metadata: {", ".join(missing)}'
        )
    digest = bead_digest(issue)
    wisker = {
        'wisker_id': f'WISKER-{issue["id"]}-{digest[:8]}',
        'bd_id': issue['id'],
        'source_bead_digest': digest,
        'source_commit_sha': source_commit_sha,
        'mission_id': metadata['mission_id'],
        'title': metadata.get('title', issue.get('title', '')),
        'objective': metadata['objective'],
        'agent_role': metadata['agent_role'],
        'autonomy_level': metadata['autonomy_level'],
        'confidence': metadata['confidence'],
        'risk': metadata['risk'],
        'allowed_paths': metadata['allowed_paths'],
        'forbidden_paths': metadata['forbidden_paths'],
        'tool_budget': metadata['tool_budget'],
        'definition_of_done': metadata['definition_of_done'],
        'validation': metadata['validation'],
        'stop_conditions': metadata['stop_conditions'],
        'required_output': metadata['required_output'],
    }
    path_errors = validate_wisker_paths(wisker)
    if path_errors:
        raise BeadsCommandError('; '.join(path_errors))
    return wisker


def validate_wisker_paths(wisker: dict[str, Any]) -> list[str]:
    """Reject scope definitions that authorize a forbidden path."""
    allowed = [str(item).replace('\\', '/').rstrip('/') for item in wisker.get('allowed_paths', [])]
    forbidden = [str(item).replace('\\', '/').rstrip('/') for item in wisker.get('forbidden_paths', [])]
    errors: list[str] = []
    for item in allowed:
        if any(item == blocked or item.startswith(blocked + '/') or blocked.startswith(item + '/') for blocked in forbidden):
            errors.append(f'forbidden path overlap: {item}')
        if item in {'.beads', '.git', 'archive'} or item.startswith(('.beads/', '.git/', 'archive/')):
            errors.append(f'protected path is not allowed: {item}')
    return errors


def write_packet(wisker: dict[str, Any]) -> Path:
    packet_path = ROOT / 'wiskers' / 'packets' / f'{wisker["wisker_id"]}.yaml'
    import yaml
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(wisker, sort_keys=False)
    if not packet_path.exists() or packet_path.read_text(encoding='utf-8') != rendered:
        packet_path.write_text(rendered, encoding='utf-8')
    return packet_path
