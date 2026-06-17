from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def validate_with_schema(instance: Any, schema_path: Path) -> list[str]:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    messages: list[str] = []
    for error in errors:
        location = '.'.join(str(part) for part in error.path) or '<root>'
        messages.append(f'{location}: {error.message}')
    return messages


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def find_yaml_files(*patterns: str) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(ROOT.glob(pattern))
    return sorted(path for path in files if path.is_file())
