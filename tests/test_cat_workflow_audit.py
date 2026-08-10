from __future__ import annotations

from pathlib import Path

from scripts.cat_workflow_audit import build_report


ROOT = Path(__file__).resolve().parents[1]


def test_local_workflow_inventory_is_deterministic_and_complete():
    report = build_report(ROOT, include_live=False)
    assert report['summary']['local_count'] == 8
    assert report['head_sha'] != 'unknown'
    assert all('source_sha' in item for item in report['local_workflows'])
    assert all('secret' not in key.lower() for key in report)


def test_live_provenance_gaps_are_explicit():
    report = build_report(ROOT, include_live=False)
    assert report['live_inventory_error'] == 'live inventory skipped by operator'
    assert report['provenance_gaps'] == []
