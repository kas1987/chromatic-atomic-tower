#!/usr/bin/env python3
"""
harness_run.py — Budget Agent Harness runner.

Executes ONE iteration of the execution loop for a given ticket.

Usage:
    python scripts/harness_run.py --ticket DEMO-001 [--worker kimi-k2.7-code:cloud]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root is always the parent of this script's directory (scripts/)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / ".agent"

# ---------------------------------------------------------------------------
# Minimal YAML loader — handles only the keys we need.
# PyYAML IS installed per spec so we use it.
# ---------------------------------------------------------------------------
try:
    import yaml  # type: ignore

    def load_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

except ImportError:  # pragma: no cover — fallback if missing
    import re as _re

    def load_yaml(path: Path) -> dict:  # type: ignore[misc]
        """Extremely minimal YAML reader for simple scalar keys only."""
        result: dict = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = _re.match(r"^(\w[\w._-]*):\s*(.+)$", line.strip())
                if m:
                    result[m.group(1)] = m.group(2).strip()
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def strip_cr(text: str) -> str:
    """Remove Windows carriage returns from Ollama responses."""
    return text.replace("\r", "")


def ollama_generate(model: str, prompt: str, endpoint: str) -> str:
    """
    Call Ollama /api/generate (stream=false).
    Returns the 'response' field as a string.
    Raises RuntimeError on failure.
    """
    url = f"{endpoint.rstrip('/')}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama unreachable at {url}: {exc}\n"
            "Is Ollama running? Start it with: ollama serve"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from Ollama: {exc}\nRaw: {raw[:500]}") from exc

    if "error" in data:
        raise RuntimeError(f"Ollama error: {data['error']}")

    return strip_cr(data.get("response", ""))


def parse_file_blocks(text: str) -> list[tuple[str, str]]:
    """
    Extract FILE: <path> + fenced code block pairs.

    Accepts:
        FILE: scripts/harness_demo.py
        ```python
        <code>
        ```

    Also handles ```python\n or ``` (no language tag).
    Returns list of (path, content) tuples.
    """
    results = []
    # Pattern: FILE: <path> on its own line, then optional blank lines, then a fenced block
    pattern = re.compile(
        r"FILE:\s*(\S+)\s*\n"           # FILE: <path>
        r"(?:[^\n]*\n)*?"               # optional intervening lines (non-greedy)
        r"```[^\n]*\n"                  # opening fence
        r"(.*?)"                        # content (lazy)
        r"```",                         # closing fence
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        path = m.group(1).strip()
        content = m.group(2)
        # Normalise path separators to forward slashes
        path = path.replace("\\", "/")
        results.append((path, content))
    return results


def is_allowed_path(path: str, allowed: list[str]) -> bool:
    """
    Return True if `path` matches any entry in the allowed list.
    Comparison is case-insensitive, normalising slashes.
    """
    norm = path.replace("\\", "/").lower()
    for a in allowed:
        a_norm = a.replace("\\", "/").strip("`").lower()
        if norm == a_norm or norm.endswith("/" + a_norm):
            return True
    return False


def run_command(cmd: str, cwd: Path) -> tuple[str, str, int]:
    """Run a shell command; return (stdout, stderr, returncode)."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout, result.stderr, result.returncode


def write_file_safe(repo_root: Path, rel_path: str, content: str) -> None:
    """Write content to repo_root/rel_path, creating parent dirs."""
    target = repo_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)


def read_text(path: Path) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def scoped_diff(repo_root: Path, files: list[str]) -> tuple[str, str, str]:
    """
    Produce a diff scoped to EXACTLY `files`, INCLUDING untracked new files and
    EXCLUDING any unrelated working-tree changes.

    Git's plain `git diff` (a) ignores untracked files and (b) shows every tracked
    modification in the tree — so a worker patch gets buried under unrelated edits
    and the worker's own new file is invisible. We mark just the worker's files
    intent-to-add (`git add -N`), diff against that scope, then reset the
    intent-to-add. No content is staged and nothing is committed; the index and
    working tree are left exactly as before.

    Returns (full_diff, name_only, stat).
    """
    files = [f for f in files if f]
    if not files:
        return "", "", ""
    spec = " ".join(f'"{f}"' for f in files)
    run_command(f"git add -N -- {spec}", repo_root)
    try:
        full, _, _ = run_command(f"git diff -- {spec}", repo_root)
        names, _, _ = run_command(f"git diff --name-only -- {spec}", repo_root)
        stat, _, _ = run_command(f"git diff --stat -- {spec}", repo_root)
    finally:
        # Undo intent-to-add so the repo is left pristine (no staged changes).
        run_command(f"git reset -q -- {spec}", repo_root)
    return full, names, stat


# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def load_queue(queue_path: Path) -> list[dict]:
    try:
        with open(queue_path, encoding="utf-8") as fh:
            data = json.loads(fh.read())
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot load queue.json: {exc}") from exc
    return data.get("items", [])


def save_queue(queue_path: Path, items: list[dict]) -> None:
    try:
        with open(queue_path, encoding="utf-8") as fh:
            data = json.loads(fh.read())
    except (json.JSONDecodeError, OSError):
        data = {}
    data["items"] = items
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(queue_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def find_ticket_item(items: list[dict], ticket_id: str) -> dict | None:
    for item in items:
        if item.get("id") == ticket_id:
            return item
    return None


# ---------------------------------------------------------------------------
# Parse allowed files from ticket markdown
# ---------------------------------------------------------------------------

def parse_allowed_files(ticket_text: str) -> list[str]:
    """Extract list items under '## Allowed Files' section."""
    allowed: list[str] = []
    in_section = False
    for line in ticket_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Allowed Files"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):  # next section
                break
            m = re.match(r"^[-*]\s+`?([^`\n]+)`?", stripped)
            if m:
                allowed.append(m.group(1).strip())
    return allowed


def parse_test_command(ticket_text: str) -> str | None:
    """Extract the pytest command from Required Commands section."""
    in_section = False
    in_fence = False
    for line in ticket_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Required Commands"):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if stripped.startswith("## ") and not in_fence:
                break
            if in_fence and "pytest" in stripped:
                return stripped
    return None


# ---------------------------------------------------------------------------
# Guardrail checks
# ---------------------------------------------------------------------------

DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+branch\s+-[Dd]\b",
    r"\bos\.remove\b",
    r"\bshutil\.rmtree\b",
    r"\bdrop\s+table\b",
    r"\bdelete\s+from\b",
    r"subprocess.*rm\b",
    r"import\s+requests\b",   # external HTTP calls
    r"pip\s+install\b",       # dep changes
    r"npm\s+install\b",
]

SENSITIVE_PATTERNS = [
    r"\bpassword\b",
    r"\bsecret\b",
    r"\bapi_key\b",
    r"\bauth\b",
    r"\bmigration\b",
    r"\.env\b",
]


def check_guardrails(content: str) -> list[str]:
    """Return list of guardrail violation descriptions found in content."""
    violations: list[str] = []
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            violations.append(f"Destructive/blocked pattern detected: {pat}")
    return violations


def check_sensitive(content: str) -> list[str]:
    """Return list of sensitive pattern matches (escalation flags, not hard blocks)."""
    flags: list[str] = []
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            flags.append(f"Sensitive pattern: {pat}")
    return flags


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_ticket(ticket_id: str, worker_model: str, bead_id: str | None = None) -> None:
    # ---- Load config -------------------------------------------------------
    routes_path = AGENT_DIR / "model_routes.yaml"
    settings_path = AGENT_DIR / "harness_settings.yaml"
    queue_path = AGENT_DIR / "queue.json"

    if not routes_path.exists():
        raise RuntimeError(f"model_routes.yaml not found: {routes_path}")
    if not settings_path.exists():
        raise RuntimeError(f"harness_settings.yaml not found: {settings_path}")

    routes = load_yaml(routes_path)
    settings = load_yaml(settings_path)  # noqa: F841 — available for future use

    # Resolve endpoint from routes
    worker_entry = routes.get("models", {}).get("worker_primary", {})
    endpoint = worker_entry.get("endpoint", "http://localhost:11434")
    reviewer_model = (
        routes.get("models", {}).get("worker_secondary", {}).get("model", "minimax-m3:cloud")
    )
    reviewer_endpoint = (
        routes.get("models", {}).get("worker_secondary", {}).get("endpoint", endpoint)
    )

    max_attempts = int(
        routes.get("budget_controls", {}).get("max_worker_retries_per_ticket", 2)
    )

    log(f"Worker model  : {worker_model}")
    log(f"Reviewer model: {reviewer_model}")
    log(f"Endpoint      : {endpoint}")
    log(f"Max attempts  : {max_attempts}")

    # ---- Load queue --------------------------------------------------------
    queue_items = load_queue(queue_path)
    ticket_item = find_ticket_item(queue_items, ticket_id)
    if ticket_item is None:
        # Add a placeholder so we can update it later
        ticket_item = {"id": ticket_id, "status": "pending"}
        queue_items.append(ticket_item)

    # ---- Load ticket file --------------------------------------------------
    ticket_path = AGENT_DIR / "tickets" / f"{ticket_id}.md"
    if not ticket_path.exists():
        raise RuntimeError(f"Ticket file not found: {ticket_path}")

    ticket_text = read_text(ticket_path)
    allowed_files = parse_allowed_files(ticket_text)
    test_command = parse_test_command(ticket_text) or f"python -m pytest -q tests/test_harness_demo.py"

    log(f"Ticket        : {ticket_id}")
    log(f"Allowed files : {allowed_files}")
    log(f"Test command  : {test_command}")

    # ---- Prepare run folder ------------------------------------------------
    run_dir = AGENT_DIR / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load worker prompt ------------------------------------------------
    worker_prompt_path = AGENT_DIR / "prompts" / "local_worker_prompt.md"
    if not worker_prompt_path.exists():
        raise RuntimeError(f"Worker prompt not found: {worker_prompt_path}")
    worker_prompt_base = read_text(worker_prompt_path)

    # ---- Build initial prompt ----------------------------------------------
    output_instruction = textwrap.dedent("""
        Output the COMPLETE final contents of each allowed file, each in its own fenced code block
        immediately preceded by a line `FILE: <path>`. Output nothing outside the required markdown sections.

        Example:
        FILE: scripts/harness_demo.py
        ```python
        # ... complete file contents here ...
        ```
    """).strip()

    def build_prompt(extra: str = "") -> str:
        parts = [
            worker_prompt_base,
            "\n\n---\n\n",
            "## Ticket\n\n",
            ticket_text,
            "\n\n---\n\n",
            output_instruction,
        ]
        if extra:
            parts += ["\n\n---\n\n", extra]
        return "".join(parts)

    # ---- Execution loop (max 2 attempts) -----------------------------------
    attempts = 0
    test_passed = False
    test_output_final = ""
    worker_response_final = ""
    guardrail_violations: list[str] = []
    files_written: list[str] = []
    escalation_notes: list[str] = []
    extra_context = ""
    diff_full = diff_names = diff_stat = ""

    while attempts < max_attempts:
        attempts += 1
        log(f"--- Worker attempt {attempts}/{max_attempts} ---")

        prompt = build_prompt(extra_context)

        # Call worker
        log("Calling worker model via Ollama...")
        try:
            worker_response = ollama_generate(worker_model, prompt, endpoint)
        except RuntimeError as exc:
            log(f"ERROR: Worker call failed: {exc}")
            escalation_notes.append(f"Attempt {attempts}: Ollama error — {exc}")
            break

        worker_response_final = worker_response
        # Save raw response
        resp_path = run_dir / f"worker_response_attempt{attempts}.md"
        resp_path.write_text(worker_response, encoding="utf-8")
        log(f"Worker response saved: {resp_path.name} ({len(worker_response)} chars)")

        # Check guardrails on raw response
        violations = check_guardrails(worker_response)
        if violations:
            log(f"GUARDRAIL VIOLATION on attempt {attempts}: {violations}")
            guardrail_violations.extend(violations)
            escalation_notes.append(
                f"Attempt {attempts}: Guardrail violations — {violations}. Stopping."
            )
            break

        sensitive_flags = check_sensitive(worker_response)
        if sensitive_flags:
            log(f"Sensitive patterns detected (escalation flag): {sensitive_flags}")
            escalation_notes.append(f"Sensitive flags on attempt {attempts}: {sensitive_flags}")

        # Parse FILE blocks
        file_blocks = parse_file_blocks(worker_response)
        if not file_blocks:
            log("WARNING: No FILE: blocks found in worker response.")
            escalation_notes.append(
                f"Attempt {attempts}: Worker produced no FILE blocks. Cannot write any files."
            )
            # Record and stop — nothing to retry with
            if attempts >= max_attempts:
                break
            extra_context = (
                "Your previous response did not include any FILE: <path> blocks with fenced code. "
                "You MUST output the complete file contents using the FILE: <path> format "
                "followed immediately by a fenced code block. Try again."
            )
            continue

        # Write allowed files, skip others
        files_written = []
        for path, content in file_blocks:
            if is_allowed_path(path, allowed_files):
                # Resolve relative to repo root
                rel = path.lstrip("/")
                write_file_safe(REPO_ROOT, rel, content)
                files_written.append(rel)
                log(f"Wrote: {rel}")
            else:
                msg = f"Attempt {attempts}: Worker tried to write non-allowed file: {path} — SKIPPED"
                log(f"GUARDRAIL: {msg}")
                guardrail_violations.append(msg)

        if not files_written:
            log("WARNING: No allowed files were written.")
            escalation_notes.append(f"Attempt {attempts}: All FILE blocks were outside allowed list.")
            if attempts >= max_attempts:
                break
            extra_context = (
                f"Your previous response tried to write files not in the allowed list: "
                f"{allowed_files}. Only write to files in that list."
            )
            continue

        # Run validation: diff SCOPED to the worker's written files only
        # (includes untracked new files, excludes unrelated working-tree edits).
        log("Computing scoped git diff for worker files...")
        diff_full, diff_names, diff_stat = scoped_diff(REPO_ROOT, files_written)
        (run_dir / "git_diff_stat.txt").write_text(diff_stat, encoding="utf-8")
        (run_dir / "git_diff_names.txt").write_text(diff_names, encoding="utf-8")
        (run_dir / "git_diff_full.txt").write_text(diff_full, encoding="utf-8")

        # Run tests
        log(f"Running tests: {test_command}")
        test_out, test_err, test_rc = run_command(test_command, REPO_ROOT)
        test_output = test_out + test_err
        test_output_final = test_output
        attempt_test_path = run_dir / f"test_output_attempt{attempts}.txt"
        attempt_test_path.write_text(test_output, encoding="utf-8")
        log(f"Test exit code: {test_rc}")
        log(f"Test output snippet: {test_output[:300]}")

        if test_rc == 0:
            test_passed = True
            log("Tests PASSED.")
            break
        else:
            log(f"Tests FAILED on attempt {attempts}.")
            if attempts < max_attempts:
                extra_context = (
                    f"Tests failed. Here is the test output:\n\n```\n{test_output}\n```\n\n"
                    "Fix the file(s) and output the complete corrected version(s) "
                    "using the FILE: <path> format."
                )
            else:
                log("Max attempts reached. Stopping worker loop.")

    # Always save the last test output to a canonical path
    (run_dir / "test_output.txt").write_text(test_output_final, encoding="utf-8")
    # Save final worker response
    (run_dir / "worker_response.md").write_text(worker_response_final, encoding="utf-8")

    # ---- Cheap review pass -------------------------------------------------
    log("Calling cheap reviewer model...")
    reviewer_prompt_path = AGENT_DIR / "prompts" / "cheap_reviewer_prompt.md"
    reviewer_prompt_base = read_text(reviewer_prompt_path) if reviewer_prompt_path.exists() else ""

    # Reuse the scoped diff so the reviewer sees ONLY the worker's contribution.
    diff_for_review = diff_full

    cheap_review_prompt = "\n\n".join([
        reviewer_prompt_base,
        f"## Ticket\n\n{ticket_text}",
        f"## Files Written\n\n" + "\n".join(f"- {f}" for f in files_written),
        f"## Diff\n\n```diff\n{diff_for_review[:8000]}\n```",
        f"## Test Results\n\n```\n{test_output_final[:4000]}\n```",
        f"## Test Passed: {test_passed}",
        f"## Guardrail Violations: {guardrail_violations}",
    ])

    try:
        cheap_review_text = ollama_generate(reviewer_model, cheap_review_prompt, reviewer_endpoint)
    except RuntimeError as exc:
        cheap_review_text = f"[Cheap review unavailable: {exc}]"
        log(f"Cheap review error: {exc}")

    (run_dir / "cheap_review.md").write_text(cheap_review_text, encoding="utf-8")
    log("Cheap review saved.")

    # ---- Assemble review packet --------------------------------------------
    log("Assembling review packet...")

    review_packet = f"""# Review Packet

## Ticket

{ticket_text}

## Files Changed

```text
{diff_names if diff_names else "(no tracked changes — new untracked files)"}
```

## Diff Summary

```text
{diff_stat if diff_stat else "(no tracked diff)"}
```

## Patch / Targeted Diff

```diff
{diff_for_review[:6000] if diff_for_review else "(no diff — files may be untracked)"}
```

## Test Commands Run

```text
{test_command}
```

## Test Results

```text
{test_output_final}
```

## Worker Self-Assessment

Worker model: {worker_model}
Attempts used: {attempts} / {max_attempts}
Files written: {files_written}
Guardrail violations: {guardrail_violations}
Escalation notes: {escalation_notes}

## Cheap Reviewer Notes

{cheap_review_text}

## Known Failures / Exceptions

Test passed: {test_passed}
Guardrail violations: {guardrail_violations if guardrail_violations else "None"}
Escalation notes: {escalation_notes if escalation_notes else "None"}

## Request to Opus

Approve, request revision, or reject this patch. Identify blocking issues and required revisions.
"""

    (run_dir / "review_packet.md").write_text(review_packet, encoding="utf-8")
    log(f"Review packet: {run_dir / 'review_packet.md'}")

    # ---- Update queue status -----------------------------------------------
    for item in queue_items:
        if item.get("id") == ticket_id:
            item["status"] = "review"
            break
    save_queue(queue_path, queue_items)
    log(f"Queue updated: {ticket_id} -> review")

    # ---- Summary -----------------------------------------------------------
    print("\n" + "=" * 60)
    print("HARNESS RUN COMPLETE")
    print("=" * 60)
    print(f"Ticket           : {ticket_id}")
    print(f"Worker model     : {worker_model}")
    print(f"Attempts used    : {attempts} / {max_attempts}")
    print(f"Test result      : {'PASSED' if test_passed else 'FAILED'}")
    print(f"Files written    : {files_written}")
    print(f"Guardrail viol.  : {len(guardrail_violations)}")
    print(f"Escalation notes : {len(escalation_notes)}")
    print(f"Review packet    : {run_dir / 'review_packet.md'}")
    print(f"Queue status     : {ticket_id} -> review (NOT done -- awaiting human approval)")
    print("=" * 60)

    # ---- Optional CAT kernel bridge ---------------------------------------
    if bead_id:
        bridge = REPO_ROOT / "scripts" / "harness_bridge.py"
        if bridge.exists():
            log(f"Bridging run into CAT kernel (bead {bead_id})...")
            br_out, br_err, br_rc = run_command(
                f'"{sys.executable}" "{bridge}" --bead {bead_id} --ticket {ticket_id}',
                REPO_ROOT,
            )
            print(br_out + br_err)
            if br_rc != 0:
                log(f"WARNING: bridge exited with code {br_rc}.")
        else:
            log(f"Bead {bead_id} supplied but {bridge} not found; skipping bridge.")

    if not test_passed:
        print("\nWARNING: Tests did not pass. Review the packet before proceeding.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Budget Agent Harness — run one ticket iteration."
    )
    parser.add_argument("--ticket", required=True, help="Ticket ID (e.g. DEMO-001)")
    parser.add_argument(
        "--worker",
        default="kimi-k2.7-code:cloud",
        help="Worker model tag (default: kimi-k2.7-code:cloud)",
    )
    parser.add_argument(
        "--bead",
        default=None,
        help="Optional CAT BEAD id to bridge this run into (e.g. BEAD-CAT-002-003). "
             "When set, emits evidence and advances the BEAD/queue after the run.",
    )
    args = parser.parse_args()

    try:
        run_ticket(args.ticket, args.worker, args.bead)
    except RuntimeError as exc:
        print(f"\nFATAL ERROR: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
