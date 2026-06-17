#!/usr/bin/env bash
# Capture current git state into a run folder. Conservative, observe-only.
# Usage: scripts/hooks/capture_git_state.sh [TICKET]   (default ticket: manual)
set -euo pipefail
TICKET="${1:-manual}"
RUN_DIR=".agent/runs/${TICKET}"
mkdir -p "$RUN_DIR"
git status --short > "$RUN_DIR/git_status.txt"
git branch --show-current > "$RUN_DIR/git_branch.txt"
echo "Captured git state -> $RUN_DIR/{git_status.txt,git_branch.txt}"
