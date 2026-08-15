from scripts.cat_changed_files_guard import check

BEAD = 'beads/completed/BEAD-CAT-A010-4C01-01.yaml'


def test_changed_files_allowed():
    result = check(BEAD, 'tests/fixtures/github/changed_files_allowed.txt')
    assert result['allowed'] is True


def test_changed_files_forbidden():
    result = check(BEAD, 'tests/fixtures/github/changed_files_forbidden.txt')
    assert result['allowed'] is False
    assert any('Forbidden path' in error for error in result['errors'])


def test_changed_files_out_of_scope():
    result = check(BEAD, 'tests/fixtures/github/changed_files_out_of_scope.txt')
    assert result['allowed'] is False
    assert any('outside BEAD allowed paths' in error for error in result['errors'])
