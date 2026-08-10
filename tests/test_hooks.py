from __future__ import annotations

from pathlib import Path

from scripts.install_hooks import install_hook


ROOT = Path(__file__).resolve().parents[1]


def test_versioned_pre_push_hook_runs_fail_closed_contract():
    source = ROOT / 'scripts/hooks/pre-push.sh'
    text = source.read_text(encoding='utf-8')
    assert 'cat_check_repo.py' in text
    assert 'cat_validate.py --all' in text
    assert 'cat_cost_guard.py --check --tier balanced' in text
    assert 'Remote branch protection remains authoritative' in text


def test_installer_dry_run_does_not_write_target(tmp_path):
    source = tmp_path / 'pre-push.sh'
    target = tmp_path / '.git/hooks/pre-push'
    source.write_text('#!/usr/bin/env bash\n', encoding='utf-8')
    result = install_hook(source, target, apply=False)
    assert result.startswith('DRY-RUN')
    assert not target.exists()


def test_installer_writes_only_explicit_target(tmp_path):
    source = tmp_path / 'pre-push.sh'
    target = tmp_path / '.git/hooks/pre-push'
    source.write_text('#!/usr/bin/env bash\n', encoding='utf-8')
    result = install_hook(source, target, apply=True)
    assert result.startswith('INSTALLED')
    assert target.read_text(encoding='utf-8') == source.read_text(encoding='utf-8')
