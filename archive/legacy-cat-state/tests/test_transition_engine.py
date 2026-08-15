from __future__ import annotations

from jsonschema import Draft202012Validator
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
SCRIPTS_PATH = ROOT_PATH / 'scripts'
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from scripts.common import ROOT, load_json, load_yaml
from scripts.cat_transition import transition_allowed, evidence_required


def test_mission_transition_allowed():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'mission', 'approved', 'in_progress')
    assert allowed is True
    assert message == 'transition allowed'


def test_bead_transition_allowed():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, _ = transition_allowed(rules, 'bead', 'active', 'in_progress')
    assert allowed is True


def test_invalid_transition_denied():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'bead', 'queued', 'completed')
    assert allowed is False
    assert 'not allowed' in message


def test_terminal_transition_denied():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    allowed, message = transition_allowed(rules, 'mission', 'learned', 'in_progress')
    assert allowed is False
    assert 'terminal' in message


def test_evidence_required_targets():
    rules = load_yaml(ROOT / 'gates/state/STATE_TRANSITION_RULES.yaml')
    # Map-style rules use evidence_required_targets; from_status is ignored
    assert evidence_required(rules, 'bead', None, 'completed') is True
    assert evidence_required(rules, 'bead', None, 'in_progress') is False


def test_transition_event_schema_accepts_sample():
    schema = load_json(ROOT / 'schemas/transition_event.schema.json')
    event = {
        'timestamp': '2026-06-17T00:00:00+00:00',
        'target_type': 'bead',
        'target_id': 'BEAD-CAT-001-001',
        'from_status': 'active',
        'to_status': 'in_progress',
        'allowed': True,
        'dry_run': True,
        'reason': 'unit test sample',
        'evidence': '',
    }
    errors = list(Draft202012Validator(schema).iter_errors(event))
    assert errors == []
