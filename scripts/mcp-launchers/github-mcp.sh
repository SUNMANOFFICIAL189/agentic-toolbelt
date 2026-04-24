#!/usr/bin/env bash
# Launcher for @modelcontextprotocol/server-github — fetches PAT from Keychain.
set -euo pipefail

SECRET=$(security find-generic-password -a "$USER" -s "claude-mcp-github-pat" -w 2>/dev/null) || {
  echo "[github-mcp-launcher] Keychain entry 'claude-mcp-github-pat' not found." >&2
  exit 1
}

export GITHUB_PERSONAL_ACCESS_TOKEN="$SECRET"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

exec npx -y @modelcontextprotocol/server-github
