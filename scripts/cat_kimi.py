#!/usr/bin/env python3
"""cat_kimi.py — thin CLI for routing straightforward tasks to Ollama-Kimi.

The CAT fleet routes labor (code/schema/test/doc drafting, lightweight review)
to a local-cloud model (kimi-k2.7-code:cloud) and keeps judgment/gating with the
orchestrator. This wrapper is the single call site for that routing.

Output is schema-gated when ``--schema`` is given: the response is parsed as
JSON and validated; on failure the call is retried once with a corrective
suffix, then the error is reported (never silently accepted).

Usage:
    python scripts/cat_kimi.py --prompt "Write a JSON schema for X"
    python scripts/cat_kimi.py --prompt-file task.md --schema schemas/finding.schema.json
    echo "review this diff: ..." | python scripts/cat_kimi.py --stdin
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = 'kimi-k2.7-code:cloud'
DEFAULT_ENDPOINT = 'http://localhost:11434/api/generate'


def kimi_generate(prompt: str, *, model: str = DEFAULT_MODEL,
                  endpoint: str = DEFAULT_ENDPOINT, timeout: int = 300) -> str:
    """Call Ollama /api/generate (stream/think false); return the response text."""
    url = endpoint if endpoint.endswith('/api/generate') else f"{endpoint.rstrip('/')}/api/generate"
    payload = json.dumps({'model': model, 'prompt': prompt, 'stream': False, 'think': False}).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama unreachable at {url}: {exc}. Start it with "
            f"OLLAMA_MODELS=\"C:/Users/<you>/.ollama/models\" ollama serve") from exc
    if 'error' in data:
        raise RuntimeError(f"Ollama error: {data['error']}")
    return (data.get('response') or '').replace('\r', '')


def _extract_json(text: str):
    """Best-effort: parse the first JSON object/array in the model output."""
    text = text.strip()
    if text.startswith('```'):
        # strip a fenced block
        text = text.split('```', 2)[1]
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    start = min((i for i in (text.find('{'), text.find('[')) if i != -1), default=-1)
    if start == -1:
        raise ValueError('no JSON found in response')
    end = max(text.rfind('}'), text.rfind(']'))
    return json.loads(text[start:end + 1])


def _validate(instance, schema_path: Path) -> list[str]:
    from jsonschema import Draft202012Validator
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    return [e.message for e in Draft202012Validator(schema).iter_errors(instance)]


def main() -> int:
    p = argparse.ArgumentParser(description='Route a straightforward task to Ollama-Kimi.')
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--prompt')
    src.add_argument('--prompt-file')
    src.add_argument('--stdin', action='store_true')
    p.add_argument('--model', default=DEFAULT_MODEL)
    p.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    p.add_argument('--schema', help='Validate the JSON response against this schema (gate)')
    p.add_argument('--out', help='Write the response to this file instead of stdout')
    args = p.parse_args()

    if args.prompt is not None:
        prompt = args.prompt
    elif args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding='utf-8')
    else:
        prompt = sys.stdin.read()

    if args.schema:
        prompt += ('\n\nRespond with ONLY a single valid JSON document that conforms '
                   'to the requested schema. No prose, no markdown fences.')

    response = kimi_generate(prompt, model=args.model, endpoint=args.endpoint)

    if args.schema:
        schema_path = Path(args.schema)
        try:
            instance = _extract_json(response)
            errors = _validate(instance, schema_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
            instance = None
        if errors:
            # One corrective retry, then fail loudly (schema-gate discipline).
            retry = (prompt + f"\n\nYour previous output failed validation: {errors[:3]}. "
                     "Return corrected JSON only.")
            response = kimi_generate(retry, model=args.model, endpoint=args.endpoint)
            try:
                instance = _extract_json(response)
                errors = _validate(instance, schema_path)
            except (ValueError, json.JSONDecodeError) as exc:
                errors = [str(exc)]
        if errors:
            print(f'SCHEMA GATE FAILED: {errors[:5]}', file=sys.stderr)
            return 1
        response = json.dumps(instance, indent=2)

    if args.out:
        Path(args.out).write_text(response + '\n', encoding='utf-8')
        print(f'wrote {args.out}')
    else:
        print(response)
    return 0


if __name__ == '__main__':
    sys.exit(main())
