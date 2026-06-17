#!/usr/bin/env python3
"""
harness_bridge.py — bridge a Budget Agent Harness run into the CAT kernel.

Given a completed harness run under `.agent/runs/<ticket>/`, this tool:
  1. Reads the run artifacts (review packet, test output, diff).
  2. Writes a CAT evidence report to `evidence/reports/<bead>_harness_run.md`.
  3. Moves the linked BEAD to a non-terminal evidence state (`validating` on pass,
     `blocked` on fail) and updates `.agent/queue.json` in lockstep.

It is intentionally read-mostly: it NEVER commits, merges, pushes, or sets a BEAD to a
terminal/`completed` state. Human approval still gates the merge.

Usage:
    python scripts/harness_bridge.py --bead BEAD-CAT-002-003 [--ticket DEMO-001]
    python scripts/harness_bridge.py --bead BEAD-CAT-002-003 --no-bead-update
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# common.py lives alongside this script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_yaml, validate_with_schema  # noqa: E402

AGENT_DIR = ROOT / ".agent"
QUEUE_PATH = AGENT_DIR / "queue.json"
BEAD_SCHEMA = ROOT / "schemas" / "bead.schema.json"
REPORTS_DIR = ROOT / "evidence" / "reports"

# Non-terminal target states only. The bridge must never set a terminal state.
PASS_BEAD_STATUS = "validating"
FAIL_BEAD_STATUS = "blocked"
PASS_QUEUE_STATUS = "review"
FAIL_QUEUE_STATUS = "blocked"


def log(msg: str) -> None:
    print(f"[bridge] {msg}", flush=True)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Queue helpers (partial-write safe)
# ---------------------------------------------------------------------------

def load_queue() -> dict:
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log(f"WARNING: could not read queue.json ({exc}); continuing without queue update.")
        return {}


def find_queue_item(queue: dict, *, ticket: str | None, bead: str) -> dict | None:
    for item in queue.get("items", []):
        if ticket and item.get("id") == ticket:
            return item
    for item in queue.get("items", []):
        if item.get("bead_id") == bead:
            return item
    return None


# ---------------------------------------------------------------------------
# Pass/fail detection from run artifacts
# ---------------------------------------------------------------------------

def detect_outcome(run_dir: Path) -> tuple[bool, str]:
    """Return (passed, rationale) from the run artifacts."""
    packet = read_text(run_dir / "review_packet.md")
    m = re.search(r"Test passed:\s*(True|False)", packet)
    if m:
        return m.group(1) == "True", "review_packet.md 'Test passed:' line"

    test_out = read_text(run_dir / "test_output.txt")
    if test_out:
        # pytest summary line, e.g. "14 passed in 0.03s" / "1 failed, 2 passed"
        if re.search(r"\b\d+ failed\b", test_out) or "error" in test_out.lower():
            return False, "test_output.txt shows failures/errors"
        if re.search(r"\b\d+ passed\b", test_out):
            return True, "test_output.txt shows only passes"
    return False, "no conclusive evidence found (defaulting to NOT passed)"


# ---------------------------------------------------------------------------
# BEAD update (targeted line edits preserve formatting)
# ---------------------------------------------------------------------------

def find_bead_file(bead_id: str) -> Path | None:
    for pattern in ("beads/active/*.yaml", "beads/examples/*.yaml"):
        for path in ROOT.glob(pattern):
            if path.stem == bead_id:
                return path
    return None


def update_bead_status(bead_path: Path, new_status: str) -> tuple[str, bool]:
    """Replace the top-level `status:` line. Returns (old_status, changed)."""
    text = bead_path.read_text(encoding="utf-8")
    m = re.search(r"^status:\s*(\S+)\s*$", text, re.MULTILINE)
    old = m.group(1) if m else "<unknown>"
    if old == new_status:
        return old, False
    new_text = re.sub(
        r"^status:\s*\S+\s*$", f"status: {new_status}", text, count=1, flags=re.MULTILINE
    )
    bead_path.write_text(new_text, encoding="utf-8")
    return old, True


def bead_is_valid(bead_path: Path) -> list[str]:
    try:
        instance = load_yaml(bead_path)
    except Exception as exc:  # pragma: no cover
        return [f"could not parse YAML after edit: {exc}"]
    return validate_with_schema(instance, BEAD_SCHEMA)


# ---------------------------------------------------------------------------
# Evidence report
# ---------------------------------------------------------------------------

def write_evidence_report(
    *, bead_id: str, ticket: str, run_dir: Path, passed: bool, rationale: str,
    bead_status_change: str, queue_status: str,
) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{bead_id}_harness_run.md"

    diff_names = read_text(run_dir / "git_diff_names.txt").strip() or "(none captured)"
    test_out = read_text(run_dir / "test_output.txt").strip() or "(no test output captured)"
    result_word = "passed" if passed else "failed"

    body = f"""# Evidence Report: {bead_id} — Harness Run

- Mission: derived from {bead_id}
- BEAD: {bead_id}
- Ticket: {ticket}
- Type: harness_run
- Validation result: {result_word}
- Created by: scripts/harness_bridge.py
- Created at: {utc_stamp()}

## Summary

Harness run for ticket `{ticket}` (BEAD `{bead_id}`) completed with tests **{result_word}**
({rationale}). The BEAD was moved to `{bead_status_change}` and the queue item to
`{queue_status}`. Status was NOT set to a terminal/done state — human approval still gates merge.

## Files changed (worker diff, names only)

```text
{diff_names}
```

## Test results

```text
{test_out[:4000]}
```

## Artifacts

| Artifact | Path |
|---|---|
| Review packet | `.agent/runs/{ticket}/review_packet.md` |
| Worker response | `.agent/runs/{ticket}/worker_response.md` |
| Cheap review | `.agent/runs/{ticket}/cheap_review.md` |
| Test output | `.agent/runs/{ticket}/test_output.txt` |
| Git diff (full) | `.agent/runs/{ticket}/git_diff_full.txt` |
| Evidence report | `evidence/reports/{bead_id}_harness_run.md` |

## Validation

```bash
python scripts/cat_validate.py --all
```

## Note on confidence

`confidence.current` on the BEAD is human-owned and is intentionally NOT auto-mutated by the
bridge. Re-score it during human/Opus review using this evidence.
"""
    out.write_text(body, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge a harness run into the CAT kernel.")
    parser.add_argument("--bead", required=True, help="BEAD id, e.g. BEAD-CAT-002-003")
    parser.add_argument("--ticket", help="Ticket id / run folder under .agent/runs/. "
                                         "If omitted, resolved from queue.json by bead_id.")
    parser.add_argument("--no-bead-update", action="store_true",
                        help="Emit evidence + update queue only; leave the BEAD status untouched.")
    args = parser.parse_args()

    bead_id = args.bead

    # Resolve ticket
    queue = load_queue()
    ticket = args.ticket
    if not ticket:
        item = find_queue_item(queue, ticket=None, bead=bead_id)
        if item:
            ticket = item.get("id")
        if not ticket:
            log(f"ERROR: no --ticket given and no queue item links bead {bead_id}.")
            return 2

    run_dir = AGENT_DIR / "runs" / ticket
    if not run_dir.exists():
        log(f"ERROR: run folder not found: {run_dir}")
        return 2

    passed, rationale = detect_outcome(run_dir)
    log(f"Outcome: {'PASS' if passed else 'FAIL'} ({rationale})")

    bead_status = PASS_BEAD_STATUS if passed else FAIL_BEAD_STATUS
    queue_status = PASS_QUEUE_STATUS if passed else FAIL_QUEUE_STATUS

    # ---- Update BEAD (optional) -------------------------------------------
    bead_change = "unchanged (--no-bead-update)"
    if not args.no_bead_update:
        bead_path = find_bead_file(bead_id)
        if not bead_path:
            log(f"WARNING: bead file for {bead_id} not found; skipping bead update.")
            bead_change = "unchanged (bead file not found)"
        else:
            old, changed = update_bead_status(bead_path, bead_status)
            errors = bead_is_valid(bead_path)
            if errors:
                # Revert on validation failure
                log(f"ERROR: bead invalid after edit; reverting. Errors: {errors}")
                # best-effort revert
                update_bead_status(bead_path, old)
                bead_change = f"reverted (would have been invalid: {errors})"
            else:
                bead_change = f"{old} -> {bead_status}" if changed else f"{old} (no change)"
                log(f"BEAD {bead_id}: status {bead_change}")

    # ---- Update queue.json -------------------------------------------------
    item = find_queue_item(queue, ticket=ticket, bead=bead_id)
    if item is not None:
        item.setdefault("bead_id", bead_id)
        item["status"] = queue_status
        queue["updated"] = utc_stamp()[:10]
        QUEUE_PATH.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
        log(f"queue.json: {ticket} -> {queue_status} (bead_id={item['bead_id']})")
    else:
        log(f"WARNING: no queue item for ticket {ticket}; queue not updated.")

    # ---- Write evidence ----------------------------------------------------
    report = write_evidence_report(
        bead_id=bead_id, ticket=ticket, run_dir=run_dir, passed=passed,
        rationale=rationale, bead_status_change=bead_change, queue_status=queue_status,
    )
    log(f"Evidence report: {report.relative_to(ROOT)}")

    print("\n" + "=" * 56)
    print("HARNESS -> CAT BRIDGE COMPLETE")
    print("=" * 56)
    print(f"BEAD          : {bead_id}  ({bead_change})")
    print(f"Ticket        : {ticket}")
    print(f"Outcome       : {'PASS' if passed else 'FAIL'}")
    print(f"Queue status  : {queue_status}")
    print(f"Evidence      : {report.relative_to(ROOT)}")
    print("No terminal/done state set — human approval still gates merge.")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
