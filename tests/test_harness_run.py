"""Unit tests for scripts/harness_run.py.

Covers the pure parsing/guardrail helpers, the queue read/write helpers, the
filesystem helpers, and the Ollama HTTP client (with urllib mocked). The full
``run_ticket`` orchestration is network/subprocess heavy and is exercised at the
helper level rather than end-to-end.
"""
from __future__ import annotations

import io
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

from scripts import harness_run as hr


# ---------------------------------------------------------------------------
# strip_cr
# ---------------------------------------------------------------------------

def test_strip_cr_removes_carriage_returns():
    assert hr.strip_cr("a\r\nb\rc") == "a\nbc"


def test_strip_cr_noop_when_clean():
    assert hr.strip_cr("plain text") == "plain text"


# ---------------------------------------------------------------------------
# parse_file_blocks
# ---------------------------------------------------------------------------

def test_parse_file_blocks_single():
    text = "FILE: scripts/demo.py\n```python\nprint('hi')\n```\n"
    blocks = hr.parse_file_blocks(text)
    assert blocks == [("scripts/demo.py", "print('hi')\n")]


def test_parse_file_blocks_multiple_and_no_lang_tag():
    text = (
        "FILE: a.py\n```python\nx = 1\n```\n"
        "some prose\n"
        "FILE: b.txt\n```\nhello\n```\n"
    )
    blocks = hr.parse_file_blocks(text)
    assert [p for p, _ in blocks] == ["a.py", "b.txt"]
    assert blocks[0][1] == "x = 1\n"
    assert blocks[1][1] == "hello\n"


def test_parse_file_blocks_normalises_backslashes():
    text = "FILE: scripts\\sub\\demo.py\n```\ncode\n```\n"
    blocks = hr.parse_file_blocks(text)
    assert blocks[0][0] == "scripts/sub/demo.py"


def test_parse_file_blocks_empty_when_no_fence():
    assert hr.parse_file_blocks("FILE: a.py\nno fence here") == []


# ---------------------------------------------------------------------------
# is_allowed_path
# ---------------------------------------------------------------------------

def test_is_allowed_path_exact_match_case_insensitive():
    assert hr.is_allowed_path("Scripts/Demo.py", ["scripts/demo.py"]) is True


def test_is_allowed_path_suffix_match():
    assert hr.is_allowed_path("repo/scripts/demo.py", ["scripts/demo.py"]) is True


def test_is_allowed_path_strips_backticks_from_allowed():
    assert hr.is_allowed_path("scripts/demo.py", ["`scripts/demo.py`"]) is True


def test_is_allowed_path_rejects_unlisted():
    assert hr.is_allowed_path("scripts/secret.py", ["scripts/demo.py"]) is False


# ---------------------------------------------------------------------------
# parse_allowed_files
# ---------------------------------------------------------------------------

def test_parse_allowed_files_extracts_section():
    ticket = (
        "# Ticket\n\n"
        "## Allowed Files\n"
        "- `scripts/a.py`\n"
        "* scripts/b.py\n\n"
        "## Required Commands\n"
        "- not a file\n"
    )
    assert hr.parse_allowed_files(ticket) == ["scripts/a.py", "scripts/b.py"]


def test_parse_allowed_files_empty_when_absent():
    assert hr.parse_allowed_files("# Ticket\n\nno section\n") == []


# ---------------------------------------------------------------------------
# parse_test_command
# ---------------------------------------------------------------------------

def test_parse_test_command_inside_fence():
    ticket = (
        "## Required Commands\n"
        "```bash\n"
        "python -m pytest -q tests/test_x.py\n"
        "```\n"
    )
    assert hr.parse_test_command(ticket) == "python -m pytest -q tests/test_x.py"


def test_parse_test_command_none_when_no_pytest():
    ticket = "## Required Commands\n```bash\nmake build\n```\n"
    assert hr.parse_test_command(ticket) is None


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("snippet", [
    "rm -rf /",
    "git push --force",
    "git reset --hard HEAD",
    "shutil.rmtree(path)",
    "DROP TABLE users",
    "DELETE FROM accounts",
])
def test_check_guardrails_flags_destructive(snippet):
    assert hr.check_guardrails(snippet)


def test_check_guardrails_clean_passes():
    assert hr.check_guardrails("def add(a, b):\n    return a + b\n") == []


@pytest.mark.parametrize("snippet", [
    "password = x",
    "api_key value",
    "pip install requests",
    "import requests",
    ".env file",
])
def test_check_sensitive_flags(snippet):
    assert hr.check_sensitive(snippet)


def test_check_sensitive_clean_passes():
    assert hr.check_sensitive("just some harmless code") == []


# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def test_load_queue_returns_items(tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text(json.dumps({"items": [{"id": "T-1"}]}), encoding="utf-8")
    assert hr.load_queue(qp) == [{"id": "T-1"}]


def test_load_queue_missing_items_key(tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text(json.dumps({"updated": "2026-01-01"}), encoding="utf-8")
    assert hr.load_queue(qp) == []


def test_load_queue_raises_on_bad_json(tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        hr.load_queue(qp)


def test_save_queue_roundtrip(tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text(json.dumps({"items": [], "meta": "keep"}), encoding="utf-8")
    hr.save_queue(qp, [{"id": "T-2", "status": "review"}])
    data = json.loads(qp.read_text(encoding="utf-8"))
    assert data["items"] == [{"id": "T-2", "status": "review"}]
    assert data["meta"] == "keep"
    assert "updated" in data


def test_save_queue_recovers_from_corrupt_existing(tmp_path):
    qp = tmp_path / "queue.json"
    qp.write_text("garbage", encoding="utf-8")
    hr.save_queue(qp, [{"id": "T-3"}])
    data = json.loads(qp.read_text(encoding="utf-8"))
    assert data["items"] == [{"id": "T-3"}]


def test_find_ticket_item_found_and_missing():
    items = [{"id": "A"}, {"id": "B"}]
    assert hr.find_ticket_item(items, "B") == {"id": "B"}
    assert hr.find_ticket_item(items, "Z") is None


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def test_write_file_safe_creates_parents(tmp_path):
    hr.write_file_safe(tmp_path, "nested/dir/out.txt", "content")
    target = tmp_path / "nested" / "dir" / "out.txt"
    assert target.read_text(encoding="utf-8") == "content"


def test_read_text_roundtrip(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello", encoding="utf-8")
    assert hr.read_text(p) == "hello"


def test_load_yaml_reads_mapping(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("key: value\nnum: 3\n", encoding="utf-8")
    assert hr.load_yaml(p) == {"key": "value", "num": 3}


# ---------------------------------------------------------------------------
# run_command / scoped_diff (real git repo in tmp)
# ---------------------------------------------------------------------------

def test_run_command_captures_output(tmp_path):
    out, err, rc = hr.run_command("echo hello", tmp_path)
    assert out.strip() == "hello"
    assert rc == 0


def test_run_command_nonzero_returncode(tmp_path):
    _, _, rc = hr.run_command("exit 7", tmp_path)
    assert rc == 7


def _init_git_repo(path: Path) -> None:
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t.t"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(cmd, cwd=path, check=True)


def test_scoped_diff_empty_for_no_files(tmp_path):
    assert hr.scoped_diff(tmp_path, []) == ("", "", "")


def test_scoped_diff_shows_untracked_new_file(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "new.py").write_text("print('x')\n", encoding="utf-8")
    full, names, stat = hr.scoped_diff(tmp_path, ["new.py"])
    assert "new.py" in names
    assert "print('x')" in full
    # repo must be left pristine — nothing staged
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert staged.stdout.strip() == ""


# ---------------------------------------------------------------------------
# ollama_generate (urllib mocked)
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_ollama_generate_success(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        return _FakeResp(json.dumps({"response": "generated\r\ntext"}))

    monkeypatch.setattr(hr.urllib.request, "urlopen", fake_urlopen)
    out = hr.ollama_generate("m", "prompt", "http://host:1234")
    assert out == "generated\ntext"
    assert captured["url"] == "http://host:1234/api/generate"


def test_ollama_generate_keeps_explicit_generate_path(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        return _FakeResp(json.dumps({"response": "ok"}))

    monkeypatch.setattr(hr.urllib.request, "urlopen", fake_urlopen)
    hr.ollama_generate("m", "p", "http://host:1234/api/generate")
    assert captured["url"] == "http://host:1234/api/generate"


def test_ollama_generate_raises_on_network_error(monkeypatch):
    def fake_urlopen(req, timeout=0):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(hr.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="Ollama unreachable"):
        hr.ollama_generate("m", "p", "http://host")


def test_ollama_generate_raises_on_bad_json(monkeypatch):
    monkeypatch.setattr(
        hr.urllib.request, "urlopen", lambda req, timeout=0: _FakeResp("not json")
    )
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        hr.ollama_generate("m", "p", "http://host")


def test_ollama_generate_raises_on_api_error_field(monkeypatch):
    monkeypatch.setattr(
        hr.urllib.request, "urlopen",
        lambda req, timeout=0: _FakeResp(json.dumps({"error": "model not found"})),
    )
    with pytest.raises(RuntimeError, match="Ollama error"):
        hr.ollama_generate("m", "p", "http://host")
