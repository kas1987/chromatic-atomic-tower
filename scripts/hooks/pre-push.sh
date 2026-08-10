#!/usr/bin/env bash
# Versioned CAT pre-push contract. Remote branch protection remains authoritative.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
PYTHON_BIN="${CAT_PYTHON:-python}"

"$PYTHON_BIN" scripts/cat_check_repo.py
"$PYTHON_BIN" scripts/cat_validate.py --all
"$PYTHON_BIN" scripts/cat_cost_guard.py --check --tier balanced
