#!/usr/bin/env bash
# Launcher for claude-code-bridge — fetches ANTHROPIC_API_KEY from Keychain.
set -euo pipefail

SECRET=$(security find-generic-password -a "$USER" -s "claude-mcp-claude-code-bridge-api-key" -w 2>/dev/null) || {
  echo "[claude-code-bridge-launcher] Keychain entry 'claude-mcp-claude-code-bridge-api-key' not found." >&2
  exit 1
}

export ANTHROPIC_API_KEY="$SECRET"
export PATH="/Users/sunil_rajput/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

exec node /Users/sunil_rajput/Desktop/claude-code-bridge/build/index.js
