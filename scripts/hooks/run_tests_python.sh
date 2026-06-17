#!/usr/bin/env bash
# Run pytest and capture output into a run folder. Never fails the task (|| true).
# Usage: scripts/hooks/run_tests_python.sh [TICKET]   (default ticket: manual)
set -uo pipefail
TICKET="${1:-manual}"
RUN_DIR=".agent/runs/${TICKET}"
mkdir -p "$RUN_DIR"
if command -v pytest >/dev/null 2>&1; then
  pytest -q > "$RUN_DIR/test_output.txt" 2>&1 || true
else
  python -m pytest -q > "$RUN_DIR/test_output.txt" 2>&1 || \
    echo "pytest not found" > "$RUN_DIR/test_output.txt"
fi
echo "Test output -> $RUN_DIR/test_output.txt"
