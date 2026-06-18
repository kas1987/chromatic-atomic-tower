"""
tests/test_harness_run.py

Comprehensive tests for scripts/harness_run.py.

All tests are fully isolated (tmp_path) and mock external calls
(Ollama API, subprocess, git) so they run offline without side effects.
"""
from __future__ import annotations

import json
import sys
import textwrap
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import harness_run


# ---------------------------------------------------------------------------
# strip_cr
# ---------------------------------------------------------------------------

def test_strip_cr_removes_carriage_returns():
    assert harness_run.strip_cr("line1\r\nline2\r\n") == "line1\nline2\n"


def test_strip_cr_noop_on_clean_text():
    text = "no carriage returns here\n"
    assert harness_run.strip_cr(text) == text


def test_strip_cr_empty_string():
    assert harness_run.strip_cr("") == ""


# ---------------------------------------------------------------------------
# parse_file_blocks
# ---------------------------------------------------------------------------

def test_parse_file_blocks_basic():
    text = textwrap.dedent("""\
        FILE: scripts/foo.py
        ```python
        def hello(): pass
        ```
    """)
    blocks = harness_run.parse_file_blocks(text)
    assert len(blocks) == 1
    path, content = blocks[0]
    assert path == "scripts/foo.py"
    assert "def hello(): pass" in content


def test_parse_file_blocks_multiple():
    text = textwrap.dedent("""\
        FILE: a.py
        ```python
        x = 1
        ```

        FILE: b.txt
        ```
        hello
        ```
    """)
    blocks = harness_run.parse_file_blocks(text)
    assert len(blocks) == 2
    assert blocks[0][0] == "a.py"
    assert blocks[1][0] == "b.txt"


def test_parse_file_blocks_normalises_backslashes():
    text = "FILE: scripts\\harness.py\n```python\npass\n```\n"
    blocks = harness_run.parse_file_blocks(text)
    assert blocks[0][0] == "scripts/harness.py"


def test_parse_file_blocks_empty_response():
    assert harness_run.parse_file_blocks("") == []


def test_parse_file_blocks_no_fence():
    # Plain text without a fenced block should produce no results
    text = "FILE: scripts/foo.py\nsome text without fence"
    assert harness_run.parse_file_blocks(text) == []


def test_parse_file_blocks_no_language_tag():
    text = "FILE: plain.txt\n```\ncontent here\n```\n"
    blocks = harness_run.parse_file_blocks(text)
    assert len(blocks) == 1
    assert "content here" in blocks[0][1]


# ---------------------------------------------------------------------------
# is_allowed_path
# ---------------------------------------------------------------------------

def test_is_allowed_path_exact_match():
    assert harness_run.is_allowed_path("scripts/foo.py", ["scripts/foo.py"])


def test_is_allowed_path_suffix_match():
    assert harness_run.is_allowed_path("deep/scripts/foo.py", ["scripts/foo.py"])


def test_is_allowed_path_case_insensitive():
    assert harness_run.is_allowed_path("SCRIPTS/Foo.py", ["scripts/foo.py"])


def test_is_allowed_path_no_match():
    assert not harness_run.is_allowed_path("scripts/bar.py", ["scripts/foo.py"])


def test_is_allowed_path_strips_backticks():
    # Allowed list entries may include backtick wrappers from Markdown
    assert harness_run.is_allowed_path("scripts/foo.py", ["`scripts/foo.py`"])


def test_is_allowed_path_empty_allowed():
    assert not harness_run.is_allowed_path("scripts/foo.py", [])


# ---------------------------------------------------------------------------
# parse_allowed_files
# ---------------------------------------------------------------------------

def test_parse_allowed_files_basic():
    ticket = textwrap.dedent("""\
        # Title

        ## Allowed Files

        - `scripts/harness_demo.py`
        - scripts/foo.py

        ## Next Section
    """)
    result = harness_run.parse_allowed_files(ticket)
    assert "scripts/harness_demo.py" in result
    assert "scripts/foo.py" in result


def test_parse_allowed_files_stops_at_next_section():
    ticket = textwrap.dedent("""\
        ## Allowed Files
        - a.py

        ## Other
        - b.py
    """)
    result = harness_run.parse_allowed_files(ticket)
    assert "a.py" in result
    assert "b.py" not in result


def test_parse_allowed_files_empty_section():
    ticket = "## Allowed Files\n\n## Required Commands\n"
    assert harness_run.parse_allowed_files(ticket) == []


def test_parse_allowed_files_no_section():
    ticket = "## Title\nSome text\n"
    assert harness_run.parse_allowed_files(ticket) == []


# ---------------------------------------------------------------------------
# parse_test_command
# ---------------------------------------------------------------------------

def test_parse_test_command_finds_pytest():
    ticket = textwrap.dedent("""\
        ## Required Commands

        ```
        python -m pytest -q tests/test_foo.py
        ```
    """)
    result = harness_run.parse_test_command(ticket)
    assert result == "python -m pytest -q tests/test_foo.py"


def test_parse_test_command_missing_section():
    assert harness_run.parse_test_command("# Title\nNo commands here") is None


def test_parse_test_command_no_pytest_line():
    ticket = textwrap.dedent("""\
        ## Required Commands

        ```
        echo hello
        ```
    """)
    assert harness_run.parse_test_command(ticket) is None


# ---------------------------------------------------------------------------
# check_guardrails
# ---------------------------------------------------------------------------

def test_check_guardrails_rm_rf():
    violations = harness_run.check_guardrails("subprocess.run('rm -rf /tmp/foo', shell=True)")
    assert any("rm" in v for v in violations)


def test_check_guardrails_git_push_force():
    violations = harness_run.check_guardrails("git push --force origin main")
    assert violations


def test_check_guardrails_os_remove():
    violations = harness_run.check_guardrails("os.remove('/etc/passwd')")
    assert violations


def test_check_guardrails_clean_code():
    assert harness_run.check_guardrails("def add(a, b): return a + b") == []


def test_check_guardrails_drop_table():
    violations = harness_run.check_guardrails("DROP TABLE users;")
    assert violations


def test_check_guardrails_shutil_rmtree():
    violations = harness_run.check_guardrails("shutil.rmtree('/tmp/build')")
    assert violations


# ---------------------------------------------------------------------------
# check_sensitive
# ---------------------------------------------------------------------------

def test_check_sensitive_password():
    flags = harness_run.check_sensitive("password = 'hunter2'")
    assert flags


def test_check_sensitive_api_key():
    flags = harness_run.check_sensitive("api_key = os.getenv('KEY')")
    assert flags


def test_check_sensitive_pip_install():
    flags = harness_run.check_sensitive("pip install requests")
    assert flags


def test_check_sensitive_import_requests():
    flags = harness_run.check_sensitive("import requests")
    assert flags


def test_check_sensitive_clean():
    assert harness_run.check_sensitive("def hello(): return 'world'") == []


# ---------------------------------------------------------------------------
# load_queue / save_queue / find_ticket_item
# ---------------------------------------------------------------------------

def test_load_queue_valid(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"items": [{"id": "T-001", "status": "pending"}]}))
    items = harness_run.load_queue(q)
    assert len(items) == 1
    assert items[0]["id"] == "T-001"


def test_load_queue_missing_items_key(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"meta": "no items key"}))
    items = harness_run.load_queue(q)
    assert items == []


def test_load_queue_malformed_json(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text("NOT JSON {{{{")
    with pytest.raises(RuntimeError, match="Cannot load queue.json"):
        harness_run.load_queue(q)


def test_load_queue_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="Cannot load queue.json"):
        harness_run.load_queue(tmp_path / "nonexistent.json")


def test_save_queue_creates_items(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"meta": "initial"}))
    items = [{"id": "T-001", "status": "review"}]
    harness_run.save_queue(q, items)
    data = json.loads(q.read_text())
    assert data["items"] == items
    assert "updated" in data


def test_save_queue_overwrites_existing_items(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text(json.dumps({"items": [{"id": "old", "status": "pending"}]}))
    new_items = [{"id": "T-002", "status": "done"}]
    harness_run.save_queue(q, new_items)
    data = json.loads(q.read_text())
    assert data["items"] == new_items


def test_save_queue_recovers_from_corrupt_json(tmp_path):
    q = tmp_path / "queue.json"
    q.write_text("CORRUPT {")
    harness_run.save_queue(q, [{"id": "X", "status": "pending"}])
    data = json.loads(q.read_text())
    assert data["items"][0]["id"] == "X"


def test_find_ticket_item_found():
    items = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    assert harness_run.find_ticket_item(items, "B")["id"] == "B"


def test_find_ticket_item_not_found():
    items = [{"id": "A"}]
    assert harness_run.find_ticket_item(items, "Z") is None


def test_find_ticket_item_empty_list():
    assert harness_run.find_ticket_item([], "A") is None


# ---------------------------------------------------------------------------
# write_file_safe
# ---------------------------------------------------------------------------

def test_write_file_safe_creates_parent_dirs(tmp_path):
    harness_run.write_file_safe(tmp_path, "a/b/c/file.txt", "hello")
    assert (tmp_path / "a" / "b" / "c" / "file.txt").read_text() == "hello"


def test_write_file_safe_overwrites(tmp_path):
    harness_run.write_file_safe(tmp_path, "file.txt", "first")
    harness_run.write_file_safe(tmp_path, "file.txt", "second")
    assert (tmp_path / "file.txt").read_text() == "second"


# ---------------------------------------------------------------------------
# read_text
# ---------------------------------------------------------------------------

def test_read_text_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("content", encoding="utf-8")
    assert harness_run.read_text(p) == "content"


# ---------------------------------------------------------------------------
# ollama_generate — mocked
# ---------------------------------------------------------------------------

def _make_mock_response(body: dict):
    """Return a mock urllib response object."""
    raw = json.dumps(body).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_ollama_generate_success():
    mock_resp = _make_mock_response({"response": "hello world\r\n"})
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = harness_run.ollama_generate("model", "prompt", "http://localhost:11434")
    assert result == "hello world\n"


def test_ollama_generate_error_field():
    mock_resp = _make_mock_response({"error": "model not found"})
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Ollama error: model not found"):
            harness_run.ollama_generate("model", "prompt", "http://localhost:11434")


def test_ollama_generate_url_error():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(RuntimeError, match="Ollama unreachable"):
            harness_run.ollama_generate("model", "prompt", "http://localhost:11434")


def test_ollama_generate_invalid_json():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"NOT JSON"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Invalid JSON from Ollama"):
            harness_run.ollama_generate("model", "prompt", "http://localhost:11434")


def test_ollama_generate_endpoint_already_has_api_path():
    """If endpoint already ends with /api/generate, don't double-append it."""
    mock_resp = _make_mock_response({"response": "ok"})
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        harness_run.ollama_generate("model", "p", "http://localhost:11434/api/generate")
    assert captured["url"].endswith("/api/generate")
    assert captured["url"].count("/api/generate") == 1


def test_ollama_generate_missing_response_key():
    """Missing 'response' key returns empty string."""
    mock_resp = _make_mock_response({"model": "x", "done": True})
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = harness_run.ollama_generate("model", "p", "http://localhost:11434")
    assert result == ""


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_success(tmp_path):
    stdout, stderr, rc = harness_run.run_command("echo hello", tmp_path)
    assert rc == 0
    assert "hello" in stdout


def test_run_command_nonzero_exit(tmp_path):
    _, _, rc = harness_run.run_command("exit 42", tmp_path)
    assert rc == 42


def test_run_command_stderr_captured(tmp_path):
    _, stderr, _ = harness_run.run_command("echo err >&2", tmp_path)
    assert "err" in stderr


# ---------------------------------------------------------------------------
# scoped_diff — mocked git
# ---------------------------------------------------------------------------

def test_scoped_diff_empty_files(tmp_path):
    full, names, stat = harness_run.scoped_diff(tmp_path, [])
    assert full == names == stat == ""


def test_scoped_diff_with_files(tmp_path):
    with patch("harness_run.run_command") as mock_cmd:
        mock_cmd.return_value = ("diff content", "", 0)
        full, names, stat = harness_run.scoped_diff(tmp_path, ["scripts/foo.py"])
    # run_command should have been called for add, diff, name-only, stat, and reset
    assert mock_cmd.call_count == 5


def test_scoped_diff_filters_empty_file_names(tmp_path):
    """Empty-string entries in files list are silently dropped."""
    with patch("harness_run.run_command") as mock_cmd:
        mock_cmd.return_value = ("", "", 0)
        harness_run.scoped_diff(tmp_path, ["", ""])
    # Only empty list remains → early return, run_command never called
    assert mock_cmd.call_count == 0


# ---------------------------------------------------------------------------
# run_ticket — integration-level with heavy mocking
# ---------------------------------------------------------------------------

def _make_agent_dir(tmp_path: Path) -> Path:
    """Create the minimal .agent directory layout for run_ticket tests."""
    agent_dir = tmp_path / ".agent"

    # model_routes.yaml
    routes_yaml = textwrap.dedent("""\
        models:
          worker_primary:
            model: test-worker:latest
            endpoint: http://localhost:11434
          worker_secondary:
            model: test-reviewer:latest
            endpoint: http://localhost:11434
        routing_rules:
          default_worker: worker_primary
          cheap_reviewer: worker_secondary
        budget_controls:
          max_worker_retries_per_ticket: 2
    """)
    (agent_dir).mkdir(parents=True, exist_ok=True)
    (agent_dir / "model_routes.yaml").write_text(routes_yaml, encoding="utf-8")

    # harness_settings.yaml
    (agent_dir / "harness_settings.yaml").write_text("timeout: 300\n", encoding="utf-8")

    # queue.json
    (agent_dir / "queue.json").write_text(
        json.dumps({"items": [{"id": "TEST-001", "status": "pending"}]}),
        encoding="utf-8",
    )

    # Ticket
    ticket_text = textwrap.dedent("""\
        # TEST-001

        ## Allowed Files

        - `scripts/harness_demo.py`

        ## Required Commands

        ```
        python -m pytest -q tests/test_harness_demo.py
        ```
    """)
    (agent_dir / "tickets").mkdir(parents=True, exist_ok=True)
    (agent_dir / "tickets" / "TEST-001.md").write_text(ticket_text, encoding="utf-8")

    # Worker prompt
    (agent_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (agent_dir / "prompts" / "local_worker_prompt.md").write_text(
        "You are a helpful coding assistant.", encoding="utf-8"
    )
    (agent_dir / "prompts" / "cheap_reviewer_prompt.md").write_text(
        "Review the diff.", encoding="utf-8"
    )

    return agent_dir


def test_run_ticket_missing_routes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", tmp_path / ".agent")
    (tmp_path / ".agent").mkdir(parents=True, exist_ok=True)
    # harness_settings.yaml exists but routes doesn't
    (tmp_path / ".agent" / "harness_settings.yaml").write_text("x: 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="model_routes.yaml not found"):
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")


def test_run_ticket_missing_settings_file(tmp_path, monkeypatch):
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", tmp_path / ".agent")
    (tmp_path / ".agent").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agent" / "model_routes.yaml").write_text("models: {}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="harness_settings.yaml not found"):
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")


def test_run_ticket_missing_ticket_file(tmp_path, monkeypatch):
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)
    with pytest.raises(RuntimeError, match="Ticket file not found"):
        harness_run.run_ticket("NONEXISTENT-999", "kimi-k2.7-code:cloud")


def test_run_ticket_worker_ollama_failure(tmp_path, monkeypatch):
    """When Ollama fails, the ticket should still be marked 'review' and sys.exit(1) called."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    def mock_ollama(model, prompt, endpoint):
        raise RuntimeError("Ollama unreachable at http://localhost:11434")

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    with pytest.raises(SystemExit) as exc_info:
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")
    assert exc_info.value.code == 1

    # Queue should still be updated to 'review'
    q = json.loads((agent_dir / "queue.json").read_text())
    assert any(i["id"] == "TEST-001" and i["status"] == "review" for i in q["items"])


def test_run_ticket_guardrail_violation_stops_loop(tmp_path, monkeypatch):
    """A guardrail-violating worker response should stop immediately."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    call_count = {"n": 0}

    def mock_ollama(model, prompt, endpoint):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "FILE: scripts/harness_demo.py\n```python\nrm -rf /\n```\n"
        # reviewer
        return "Looks risky."

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    with pytest.raises(SystemExit) as exc_info:
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")
    assert exc_info.value.code == 1
    # Should only have called worker once (stopped on violation) + reviewer once
    assert call_count["n"] <= 2


def test_run_ticket_no_file_blocks_retries(tmp_path, monkeypatch):
    """When worker produces no FILE blocks, the loop retries (up to max_attempts)."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    responses = iter([
        "Sorry, I cannot produce that.",  # no FILE blocks — attempt 1
        "Still no FILE blocks.",           # no FILE blocks — attempt 2 (max)
        "Cheap reviewer says LGTM",        # reviewer
    ])

    def mock_ollama(model, prompt, endpoint):
        return next(responses)

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    with pytest.raises(SystemExit) as exc_info:
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")
    assert exc_info.value.code == 1


def test_run_ticket_happy_path(tmp_path, monkeypatch):
    """Worker produces valid FILE block and tests pass → exit 0."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    worker_response = textwrap.dedent("""\
        FILE: scripts/harness_demo.py
        ```python
        def add(a, b): return a + b
        def is_even(n): return n % 2 == 0
        def slugify(s): return '-'.join(s.lower().split())
        ```
    """)

    call_count = {"n": 0}

    def mock_ollama(model, prompt, endpoint):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return worker_response
        return "LGTM"

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    # Mock run_command so tests "pass"
    def mock_run_command(cmd, cwd):
        if "pytest" in cmd:
            return "5 passed in 0.05s", "", 0
        # git commands
        return "", "", 0

    monkeypatch.setattr(harness_run, "run_command", mock_run_command)

    # run_ticket should complete without SystemExit when tests pass
    harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")

    # Verify run artifacts
    run_dir = agent_dir / "runs" / "TEST-001"
    assert (run_dir / "worker_response.md").exists()
    assert (run_dir / "test_output.txt").exists()
    assert (run_dir / "review_packet.md").exists()

    # Queue should be 'review'
    q = json.loads((agent_dir / "queue.json").read_text())
    assert any(i["id"] == "TEST-001" and i["status"] == "review" for i in q["items"])


def test_run_ticket_new_ticket_added_to_queue(tmp_path, monkeypatch):
    """If ticket is not in queue.json, a placeholder is added."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    # Start with an empty queue (no TEST-001 entry)
    (agent_dir / "queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")

    def mock_ollama(model, prompt, endpoint):
        raise RuntimeError("offline")

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    with pytest.raises(SystemExit):
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")

    q = json.loads((agent_dir / "queue.json").read_text())
    ids = [i["id"] for i in q["items"]]
    assert "TEST-001" in ids


def test_run_ticket_files_outside_allowed_list_skipped(tmp_path, monkeypatch):
    """Files not in the allowed list must not be written."""
    agent_dir = _make_agent_dir(tmp_path)
    monkeypatch.setattr(harness_run, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness_run, "AGENT_DIR", agent_dir)

    worker_response = textwrap.dedent("""\
        FILE: /etc/passwd
        ```
        root:x:0:0:root:/root:/bin/bash
        ```
    """)

    call_count = {"n": 0}

    def mock_ollama(model, prompt, endpoint):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            return worker_response
        return "Review notes."

    monkeypatch.setattr(harness_run, "ollama_generate", mock_ollama)

    def mock_run_command(cmd, cwd):
        return "", "", 0

    monkeypatch.setattr(harness_run, "run_command", mock_run_command)

    with pytest.raises(SystemExit):
        harness_run.run_ticket("TEST-001", "kimi-k2.7-code:cloud")

    # /etc/passwd must not have been written
    assert not (tmp_path / "etc" / "passwd").exists()
