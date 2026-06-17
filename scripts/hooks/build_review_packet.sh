#!/usr/bin/env bash
# Assemble a review packet from captured evidence in a run folder. Observe-only.
# Usage: scripts/hooks/build_review_packet.sh [TICKET]   (default ticket: manual)
set -euo pipefail
TICKET="${1:-manual}"
RUN_DIR=".agent/runs/${TICKET}"
mkdir -p "$RUN_DIR"
OUT="$RUN_DIR/review_packet.md"
{
  echo "# Review Packet (${TICKET})"
  echo
  echo "## Ticket"
  cat ".agent/tickets/${TICKET}.md" 2>/dev/null || echo "MISSING: .agent/tickets/${TICKET}.md"
  echo
  echo "## Git Status"
  cat "$RUN_DIR/git_status.txt" 2>/dev/null || git status --short
  echo
  echo "## Diff Stat"
  cat "$RUN_DIR/git_diff_stat.txt" 2>/dev/null || git diff --stat
  echo
  echo "## Test Report"
  cat "$RUN_DIR/test_output.txt" 2>/dev/null || echo "MISSING: test_output.txt"
  echo
  echo "## Cheap Review"
  cat "$RUN_DIR/cheap_review.md" 2>/dev/null || echo "MISSING: cheap_review.md"
  echo
  echo "## Final Review Request"
  echo "Return APPROVE, REQUEST_REVISION, or REJECT with evidence-based reasoning."
} > "$OUT"
echo "Review packet -> $OUT"
