from scripts.cat_issue_intake import scaffold


def test_issue_intake_scaffolds_mission(tmp_path):
    out = scaffold('tests/fixtures/github/issue_intake.json', tmp_path)
    assert out.exists()
    assert 'mission_id: MP-CAT-DRAFT' in out.read_text(encoding='utf-8')
