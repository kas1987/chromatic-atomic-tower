from __future__ import annotations

import json
from pathlib import Path

from scripts.cat_ci_cd_baseline import collect


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_reproduces_historical_17_warning_result():
    report = collect(ROOT, ROOT / 'evidence/reports/ci-cd-audit/2026-08-10.json')
    assert report['historical_baseline']['strict_warning_count'] == 17
    assert report['current_tiers']['none']['failure_count'] == 0
    assert report['current_tiers']['strict']['failure_count'] == 0
    assert report['rollout']['strict_clean'] is True


def test_baseline_requires_numeric_prior_evidence(tmp_path):
    previous = tmp_path / 'prior.json'
    previous.write_text(json.dumps({'evidence': {'strict_cost_guard': 'unknown'}}), encoding='utf-8')
    try:
        collect(ROOT, previous)
    except ValueError as exc:
        assert 'numeric strict warning baseline' in str(exc)
    else:  # pragma: no cover
        raise AssertionError('missing baseline must fail closed')
