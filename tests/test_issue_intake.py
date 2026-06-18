import json

import pytest
import yaml

from scripts.cat_issue_intake import safe_mission_id, scaffold, slugify


def test_issue_intake_scaffolds_mission(tmp_path):
    out = scaffold('tests/fixtures/github/issue_intake.json', tmp_path)
    assert out.exists()
    assert 'mission_id: MP-CAT-DRAFT' in out.read_text(encoding='utf-8')


@pytest.mark.parametrize("value,expected", [
    ("Hello World", "hello_world"),
    ("  Spaced  Out  ", "spaced_out"),
    ("Mixed-CASE/slash", "mixed_case_slash"),
    ("", "draft_mission"),
    ("***", "draft_mission"),
])
def test_slugify(value, expected):
    assert slugify(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("MP-CAT-A006-4C01", "MP-CAT-A006-4C01"),
    ("../escape", "___escape"),
    ("a/b/c", "a_b_c"),
    ("", "MP-CAT-DRAFT"),
])
def test_safe_mission_id(value, expected):
    assert safe_mission_id(value) == expected


def test_scaffold_uses_fields_and_defaults(tmp_path):
    issue = tmp_path / "issue.json"
    issue.write_text(json.dumps({
        "title": "Build Thing",
        "mission_id": "MP-CAT-A007-4C01",
        "body": "Do the thing well.",
        "level": "M3",
        "allowed_paths": ["scripts/"],
        "definition_of_done": ["thing built"],
    }), encoding="utf-8")
    out = scaffold(issue, tmp_path / "out")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["mission_id"] == "MP-CAT-A007-4C01"
    assert data["title"] == "Build Thing"
    assert data["level"] == "M3"
    assert data["objective"] == "Do the thing well."
    assert data["allowed_paths"] == ["scripts/"]
    assert data["definition_of_done"] == ["thing built"]
    # forbidden paths are always injected
    assert ".env" in data["forbidden_paths"]


def test_scaffold_objective_falls_back_to_title(tmp_path):
    issue = tmp_path / "issue.json"
    issue.write_text(json.dumps({"title": "Only Title"}), encoding="utf-8")
    out = scaffold(issue, tmp_path / "out")
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["objective"] == "Only Title"
    assert data["definition_of_done"] == ['Draft reviewed by Orchestrator']


def test_scaffold_sanitises_malicious_mission_id(tmp_path):
    issue = tmp_path / "issue.json"
    issue.write_text(json.dumps({
        "title": "X", "mission_id": "../../etc/passwd",
    }), encoding="utf-8")
    out = scaffold(issue, tmp_path / "out")
    # output must stay within the output dir
    assert (tmp_path / "out") in out.parents
