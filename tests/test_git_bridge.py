from scripts.cat_git_bridge import check_branch, check_commit, check_title, validate_pr

A010_TITLE = '[MP-CAT-A010-4C01][BEAD-CAT-A010-4C01-01] Define GitHub governance contract'
A010_BRANCH = 'feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract'
A010_BEAD = 'beads/completed/BEAD-CAT-A010-4C01-01.yaml'
LEGACY_TITLE = '[MP-CAT-005][BEAD-CAT-005-001] Define GitHub governance contract'
LEGACY_BRANCH = 'feat/mp-cat-005-bead-cat-005-001-github-contract'


def test_pr_title_extracts_new_format_ids():
    ok, mission, bead, err = check_title(A010_TITLE)
    assert ok
    assert mission == 'MP-CAT-A010-4C01'
    assert bead == 'BEAD-CAT-A010-4C01-01'
    assert err == ''


def test_pr_title_extracts_legacy_ids():
    ok, mission, bead, err = check_title(LEGACY_TITLE)
    assert ok
    assert mission == 'MP-CAT-005'
    assert bead == 'BEAD-CAT-005-001'


def test_branch_extracts_new_format_ids():
    ok, mission, bead, err = check_branch(A010_BRANCH)
    assert ok
    assert mission == 'MP-CAT-A010-4C01'
    assert bead == 'BEAD-CAT-A010-4C01-01'


def test_branch_extracts_legacy_ids():
    ok, mission, bead, err = check_branch(LEGACY_BRANCH)
    assert ok
    assert mission == 'MP-CAT-005'
    assert bead == 'BEAD-CAT-005-001'


def test_commit_requires_tokens():
    ok, err = check_commit(A010_TITLE, 'MP-CAT-A010-4C01', 'BEAD-CAT-A010-4C01-01')
    assert ok
    assert err == ''


def test_validate_pr_happy_path_new_format():
    report = validate_pr(
        A010_TITLE,
        A010_BRANCH,
        A010_TITLE,
        A010_BEAD,
        'tests/fixtures/github/changed_files_allowed.txt',
        False,
    )
    assert report['status'] == 'passed'


def test_validate_pr_happy_path_legacy():
    report = validate_pr(
        LEGACY_TITLE,
        LEGACY_BRANCH,
        LEGACY_TITLE,
        A010_BEAD,
        'tests/fixtures/github/changed_files_allowed.txt',
        False,
    )
    assert report['status'] == 'passed'
