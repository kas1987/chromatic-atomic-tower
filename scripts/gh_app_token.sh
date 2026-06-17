#!/usr/bin/env bash
# Get a GitHub App installation token, using a local cache when still valid.
# Usage: gh_app_token.sh [--force]
#   Prints a ghs_... token to stdout (valid ~1 hour).
#   In scripts: export GITHUB_TOKEN="$(bash scripts/gh_app_token.sh)"
#
# Required env vars (add to .env or export before calling):
#   GITHUB_APP_ID                  Client ID or numeric App ID
#   GITHUB_APP_PRIVATE_KEY_PATH    path to .pem file
#   GITHUB_APP_INSTALLATION_ID     installation ID (optional — auto-detected if only one)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${REPO_ROOT}/.github_app_token_cache"
SCRIPT="${REPO_ROOT}/scripts/github_app_token.py"

# Load .env if present (never committed — see .gitignore)
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a; source "${REPO_ROOT}/.env"; set +a
fi

# Use cached token if still valid (expire 5 min early for safety)
if [[ "$*" != *"--force"* && -f "$CACHE" ]]; then
  expires=$(python3 -c "import json, sys; d=json.load(open(sys.argv[1])); print(int(d['expires_at']))" "$CACHE" 2>/dev/null || echo 0)
  now=$(date +%s)
  if [[ $now -lt $(( expires - 300 )) ]]; then
    python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['token'])" "$CACHE"
    exit 0
  fi
fi

# Generate fresh token
token=$(python3 "$SCRIPT" token ${GITHUB_APP_INSTALLATION_ID:+--install-id "$GITHUB_APP_INSTALLATION_ID"})
if [[ -z "$token" ]]; then
  echo "ERROR: failed to get GitHub App token" >&2
  exit 1
fi

# Cache with 1-hour expiry
python3 -c "
import json, sys, time
with open(sys.argv[2], 'w') as f:
    json.dump({'token': sys.argv[1], 'expires_at': time.time() + 3600}, f)
" "$token" "$CACHE"

echo "$token"
