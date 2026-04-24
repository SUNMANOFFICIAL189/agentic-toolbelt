#!/usr/bin/env bash
# Launcher for gemini-bridge — fetches GEMINI_API_KEY from Keychain.
set -euo pipefail

SECRET=$(security find-generic-password -a "$USER" -s "claude-mcp-gemini-bridge-api-key" -w 2>/dev/null) || {
  echo "[gemini-bridge-launcher] Keychain entry 'claude-mcp-gemini-bridge-api-key' not found." >&2
  exit 1
}

export GEMINI_API_KEY="$SECRET"
export PATH="/Users/sunil_rajput/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

exec node /Users/sunil_rajput/Desktop/GEMINI_BRIDGE/gemini-bridge/build/index.js
