"""Tests for scripts/cat_merge_ready.py classification and reporting.

The merge actions shell out to the `gh` CLI; here we cover the pure
classification (ready / behind / blocked) and labelling logic, and drive
``main`` in dry-run mode with ``list_open`` monkeypatched so no `gh` call is
made.
"""
from __future__ import annotations

import sys

import cat_merge_ready as mr


def _pr(number, mergeable, state, title="t"):
    return {
        "number": number, "mergeable": mergeable,
        "mergeStateStatus": state, "title": title, "headRefName": "br",
    }


def test_classify_partitions_by_state():
    prs = [
        _pr(1, "MERGEABLE", "CLEAN"),
        _pr(2, "MERGEABLE", "BEHIND"),
        _pr(3, "CONFLICTING", "DIRTY"),
        _pr(4, "MERGEABLE", "BLOCKED"),
    ]
    ready, behind, blocked = mr.classify(prs)
    assert [p["number"] for p in ready] == [1]
    assert [p["number"] for p in behind] == [2]
    assert [p["number"] for p in blocked] == [3, 4]


def test_classify_empty():
    assert mr.classify([]) == ([], [], [])


def test_label_format():
    assert mr.label(_pr(7, "MERGEABLE", "CLEAN", "Add feature")) == \
        "#7 [MERGEABLE/CLEAN] Add feature"


def test_main_dry_run_reports_without_gh(monkeypatch, capsys):
    prs = [
        _pr(1, "MERGEABLE", "CLEAN", "ready one"),
        _pr(2, "MERGEABLE", "BEHIND", "behind one"),
        _pr(3, "CONFLICTING", "DIRTY", "blocked one"),
    ]
    monkeypatch.setattr(mr, "list_open", lambda base: prs)
    monkeypatch.setattr(sys, "argv", ["cat_merge_ready.py", "--base", "main"])
    assert mr.main() == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "MERGE  #1" in out
    assert "BEHIND #2" in out
    assert "SKIP   #3" in out
    assert "1 ready, 1 behind, 1 blocked" in out


def test_main_dry_run_no_ready_breaks_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(mr, "list_open", lambda base: [_pr(9, "CONFLICTING", "DIRTY")])
    monkeypatch.setattr(sys, "argv", ["cat_merge_ready.py"])
    assert mr.main() == 0
    out = capsys.readouterr().out
    assert "Merged 0 PR(s)" in out
    assert "still blocked" in out
