#!/usr/bin/env bash
# Capture git diff (stat + full patch) into a run folder. Conservative, observe-only.
# Usage: scripts/hooks/capture_diff.sh [TICKET]   (default ticket: manual)
set -euo pipefail
TICKET="${1:-manual}"
RUN_DIR=".agent/runs/${TICKET}"
mkdir -p "$RUN_DIR"
git diff --stat > "$RUN_DIR/git_diff_stat.txt"
git diff --name-only > "$RUN_DIR/git_diff_names.txt"
git diff > "$RUN_DIR/git_diff_full.txt"
echo "Captured diff -> $RUN_DIR/git_diff_*.txt"
