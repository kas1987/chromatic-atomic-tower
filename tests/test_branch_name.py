from scripts.cat_branch_name import build, validate

A010_BRANCH = 'feat/mp-cat-a010-4c01-bead-cat-a010-4c01-01-github-contract'


def test_build_branch_name_new_format():
    branch = build('feat', 'MP-CAT-A010-4C01', 'BEAD-CAT-A010-4C01-01', 'GitHub Contract')
    assert branch == A010_BRANCH
    assert validate(branch)


def test_build_branch_name_legacy():
    branch = build('feat', 'MP-CAT-005', 'BEAD-CAT-005-001', 'GitHub Contract')
    assert branch == 'feat/mp-cat-005-bead-cat-005-001-github-contract'
    assert validate(branch)


def test_reject_bad_branch_name():
    assert not validate('feature/random')
