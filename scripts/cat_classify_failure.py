#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
try:
    from common import ROOT, validate_with_schema
except ModuleNotFoundError:
    from scripts.common import ROOT, validate_with_schema

ROUTES = {
    'schema_failure': ('medium', 'Builder or Scribe', False, True, 'Fix schema structure or required fields.'),
    'state_failure': ('high', 'Orchestrator', False, False, 'Review state transition rules and tower state.'),
    'evidence_failure': ('medium', 'Scribe or Auditor', False, False, 'Attach real evidence or correct bundle references.'),
    'test_failure': ('medium', 'Builder', False, False, 'Fix implementation or update tests through normal review.'),
    'security_failure': ('critical', 'Security and Human Gate', True, False, 'Stop and escalate security-sensitive failure.'),
    'scope_failure': ('high', 'Auditor', False, False, 'Review BEAD allowed paths and changed files.'),
    'unknown_failure': ('high', 'Human Gate', True, False, 'Classify manually before continuing.'),
}

KEYWORDS = [
    ('security_failure', ['secret', 'token', 'credential', '.env', 'production', 'deploy']),
    ('scope_failure', ['forbidden path', 'outside allowed', 'scope']),
    ('evidence_failure', ['evidence', 'bundle', 'artifact', 'closeout']),
    ('state_failure', ['state', 'transition', 'terminal']),
    ('schema_failure', ['schema', 'required property', 'validation failed', 'yaml']),
    ('test_failure', ['pytest', 'test failed', 'assertion', 'unit test']),
]

def infer_failure_type(check: str, message: str) -> str:
    text = f'{check} {message}'.lower()
    for failure_type, words in KEYWORDS:
        if any(word in text for word in words):
            return failure_type
    return 'unknown_failure'

def classify(check: str, message: str) -> dict:
    failure_type = infer_failure_type(check, message)
    severity, route, human_gate, self_heal, action = ROUTES[failure_type]
    return {
        'failure_type': failure_type,
        'severity': severity,
        'route_to': route,
        'human_gate_required': human_gate,
        'self_heal_allowed': self_heal,
        'message': message,
        'check': check,
        'recommended_action': action,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description='Classify CAT CI failures for routing.')
    parser.add_argument('--check', required=True)
    parser.add_argument('--message', required=True)
    args = parser.parse_args()
    result = classify(args.check, args.message)
    errors = validate_with_schema(result, ROOT / 'schemas/ci_failure.schema.json')
    if errors:
        for error in errors:
            print(error)
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
