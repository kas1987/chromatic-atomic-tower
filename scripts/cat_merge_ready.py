#!/usr/bin/env python3
"""
cat_merge_ready.py — deterministically merge all ready PRs into a base branch.

Operator-plane automation (CAT_MANIFEST §6.1): no LLM, no judgement — it only
merges PRs GitHub already reports as safe to merge. Defaults to a dry run.

A PR is "ready" when `mergeable == MERGEABLE` and `mergeStateStatus == CLEAN`
(GitHub's signal that the branch is up to date, all required checks pass, and
there are no conflicts). Anything else is skipped with a printed reason.

Usage:
    python scripts/cat_merge_ready.py                 # dry run (default)
    python scripts/cat_merge_ready.py --execute       # actually merge
    python scripts/cat_merge_ready.py --execute --update-behind   # rebase BEHIND PRs and retry
    python scripts/cat_merge_ready.py --base master --method squash --no-delete-branch

Requires the `gh` CLI, authenticated. Never force-pushes; merges are server-side.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

READY_STATES = {"CLEAN"}          # safe to merge
UPDATABLE_STATES = {"BEHIND"}     # mergeable but needs the base merged in first


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], text=True, capture_output=True, check=check)


def list_open(base: str) -> list[dict]:
    cp = gh(["pr", "list", "--base", base, "--state", "open",
             "--json", "number,title,mergeable,mergeStateStatus,headRefName"])
    return json.loads(cp.stdout or "[]")


def classify(prs: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    ready, behind, blocked = [], [], []
    for pr in prs:
        if pr["mergeable"] == "MERGEABLE" and pr["mergeStateStatus"] in READY_STATES:
            ready.append(pr)
        elif pr["mergeable"] == "MERGEABLE" and pr["mergeStateStatus"] in UPDATABLE_STATES:
            behind.append(pr)
        else:
            blocked.append(pr)
    return ready, behind, blocked


def label(pr: dict) -> str:
    return f"#{pr['number']} [{pr['mergeable']}/{pr['mergeStateStatus']}] {pr['title']}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge all ready PRs into a base branch (dry run by default).")
    ap.add_argument("--base", default="master")
    ap.add_argument("--execute", action="store_true", help="Actually merge (default is dry run).")
    ap.add_argument("--method", choices=["merge", "squash", "rebase"], default="merge")
    ap.add_argument("--no-delete-branch", action="store_true")
    ap.add_argument("--update-behind", action="store_true",
                    help="Run `gh pr update-branch` on MERGEABLE/BEHIND PRs, then retry.")
    args = ap.parse_args()

    merged: list[int] = []
    # Iterate: merging one PR can push siblings BEHIND, so re-query each round.
    for _ in range(50):  # generous round cap; real PR counts are tiny
        prs = list_open(args.base)
        ready, behind, blocked = classify(prs)

        if not ready:
            if args.execute and args.update_behind and behind:
                for pr in behind:
                    print(f"update-branch {label(pr)}")
                    gh(["pr", "update-branch", str(pr["number"])], check=False)
                continue  # re-query and retry
            break

        pr = ready[0]
        if not args.execute:
            # Dry run: report everything in one pass and stop.
            print("DRY RUN -- would merge (in order, re-checking after each):")
            for p in ready:
                print(f"  MERGE  {label(p)}")
            for p in behind:
                print(f"  BEHIND {label(p)}  (use --update-behind to rebase then merge)")
            for p in blocked:
                print(f"  SKIP   {label(p)}")
            print(f"\n{len(ready)} ready, {len(behind)} behind, {len(blocked)} blocked. "
                  f"Re-run with --execute to merge.")
            return 0

        # Execute: merge one, then loop to re-query.
        cmd = ["pr", "merge", str(pr["number"]), f"--{args.method}"]
        if not args.no_delete_branch:
            cmd.append("--delete-branch")
        print(f"merging {label(pr)} ...")
        cp = gh(cmd, check=False)
        if cp.returncode != 0:
            print(f"  FAILED: {cp.stderr.strip()}", file=sys.stderr)
            return 1
        merged.append(pr["number"])
        print(f"  merged #{pr['number']}")

    # Final report
    prs = list_open(args.base)
    _, behind, blocked = classify(prs)
    print(f"\nMerged {len(merged)} PR(s): {merged or '(none)'}")
    for pr in behind:
        print(f"  still BEHIND: {label(pr)}  (--update-behind to handle)")
    for pr in blocked:
        print(f"  still blocked: {label(pr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
