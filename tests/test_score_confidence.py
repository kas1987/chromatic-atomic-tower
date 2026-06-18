"""Tests for scripts/cat_score_confidence.py.

Covers the decision banding, the weighted-sum scoring via the CLI in both
--dry-run and --scores modes, and the report-driven error paths.
"""
from __future__ import annotations

import json
import sys

import pytest

import cat_score_confidence as sc


@pytest.mark.parametrize("score,expected", [
    (95, "auto_proceed"),
    (90, "auto_proceed"),
    (80, "proceed_with_review"),
    (70, "proceed_with_review"),
    (60, "self_heal"),
    (50, "self_heal"),
    (10, "escalate_or_block"),
])
def test_decision_bands(score, expected):
    assert sc.decision(score) == expected


def test_weights_sum_to_one():
    assert round(sum(sc.WEIGHTS.values()), 6) == 1.0


def test_main_dry_run_uses_placeholder(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cat_score_confidence.py", "--dry-run"])
    assert sc.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["confidence_score"] == 90.0
    assert out["decision"] == "auto_proceed"


def test_main_with_explicit_scores(capsys, monkeypatch):
    scores = json.dumps({k: 50 for k in sc.WEIGHTS})
    monkeypatch.setattr(sys, "argv", [
        "cat_score_confidence.py", "--dry-run", "--scores", scores,
    ])
    assert sc.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["confidence_score"] == 50.0
    assert out["decision"] == "self_heal"


def test_main_writes_report_when_not_dry_run(tmp_path, capsys, monkeypatch):
    scores = json.dumps({k: 80 for k in sc.WEIGHTS})
    monkeypatch.setattr(sys, "argv", [
        "cat_score_confidence.py", "--root", str(tmp_path),
        "--mission", "MP-CAT-S001-4C01", "--scores", scores,
    ])
    assert sc.main() == 0
    out_file = tmp_path / "evidence/reports/MP-CAT-S001-4C01_confidence_score.json"
    assert out_file.exists()
    written = json.loads(out_file.read_text(encoding="utf-8"))
    assert written["decision"] == "proceed_with_review"


def test_main_errors_when_no_report_and_no_scores(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "cat_score_confidence.py", "--root", str(tmp_path), "--mission", "MP-CAT-X",
    ])
    assert sc.main() == 1
    assert "no validation report" in capsys.readouterr().out


def test_main_errors_on_draft_report(tmp_path, capsys, monkeypatch):
    report_dir = tmp_path / "evidence" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "MP-CAT-X_validation_report.json").write_text(
        json.dumps({"status": "draft", "gate_scores": {}}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", [
        "cat_score_confidence.py", "--root", str(tmp_path), "--mission", "MP-CAT-X",
    ])
    assert sc.main() == 1
    assert "draft state" in capsys.readouterr().out


def test_main_errors_on_report_without_scores(tmp_path, capsys, monkeypatch):
    report_dir = tmp_path / "evidence" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "MP-CAT-X_validation_report.json").write_text(
        json.dumps({"status": "final", "gate_scores": {}}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", [
        "cat_score_confidence.py", "--root", str(tmp_path), "--mission", "MP-CAT-X",
    ])
    assert sc.main() == 1
    assert "no gate_scores" in capsys.readouterr().out
