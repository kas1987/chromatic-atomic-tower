"""
tests/test_ci_workflow.py

Regression test for the CAT CI workflow. Ensures the validate job actually runs
the pytest suite (closing the 'CI does not run pytest' gap) and that the push
trigger targets the real default branch (master, not main).
"""

import os

import yaml

WORKFLOW = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows", "validate-cat.yml",
)


def _load():
    with open(WORKFLOW, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_workflow_parses():
    wf = _load()
    assert "jobs" in wf and "validate" in wf["jobs"]


def test_validate_job_runs_pytest():
    wf = _load()
    steps = wf["jobs"]["validate"]["steps"]
    runs = [str(s.get("run", "")) for s in steps]
    assert any("pytest" in r for r in runs), "validate job must run pytest"


def test_push_trigger_includes_master():
    wf = _load()
    # PyYAML parses the bare key `on:` as the boolean True, so check both forms.
    triggers = wf.get("on", wf.get(True, {})) or {}
    branches = (triggers.get("push") or {}).get("branches") or []
    assert "master" in branches, "push trigger must include master"
