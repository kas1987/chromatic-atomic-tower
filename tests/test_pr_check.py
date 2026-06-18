from scripts.cat_pr_check import check_scope, load_changed_files


def test_pr_check_allows_scoped_files():
    changed = load_changed_files('tests/fixtures/ci/changed_files_allowed.txt')
    result = check_scope('MP-CAT-003', 'BEAD-CAT-003-001', changed)
    assert result['status'] == 'passed'
    assert result['failures'] == []


def test_pr_check_blocks_forbidden_path():
    changed = load_changed_files('tests/fixtures/ci/changed_files_forbidden.txt')
    result = check_scope('MP-CAT-003', 'BEAD-CAT-003-001', changed)
    assert result['status'] == 'failed'
    assert any('forbidden path' in item for item in result['failures'])


def test_pr_check_blocks_outside_scope():
    changed = load_changed_files('tests/fixtures/ci/changed_files_outside_scope.txt')
    result = check_scope('MP-CAT-003', 'BEAD-CAT-003-001', changed)
    assert result['status'] == 'failed'
    assert any('outside allowed paths' in item for item in result['failures'])
