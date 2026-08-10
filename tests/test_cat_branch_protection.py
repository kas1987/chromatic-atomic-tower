from __future__ import annotations

from scripts.cat_branch_protection_audit import evaluate_protection


def test_current_style_protection_is_noncompliant():
    result = evaluate_protection({
        'required_status_checks': {'contexts': ['validate', 'cat-ci']},
        'required_pull_request_reviews': None,
        'required_conversation_resolution': {'enabled': False},
        'enforce_admins': {'enabled': False},
        'allow_force_pushes': {'enabled': False},
        'allow_deletions': {'enabled': False},
    })
    assert result['compliant'] is False
    assert result['missing_required_checks']


def test_proposed_protection_fixture_is_compliant():
    result = evaluate_protection({
        'required_status_checks': {'contexts': ['validate', 'cat-ci', 'CAT Governance CI', 'LOGHOUSE CI']},
        'required_pull_request_reviews': {'required_approving_review_count': 1},
        'required_conversation_resolution': {'enabled': True},
        'enforce_admins': {'enabled': True},
        'allow_force_pushes': {'enabled': False},
        'allow_deletions': {'enabled': False},
    })
    assert result['compliant'] is True
