#!/usr/bin/env bash
# Launcher for reddit-mcp — fetches REDDIT_CLIENT_SECRET from macOS Keychain
# at spawn time and passes it to the server as an env var.
set -euo pipefail

SECRET=$(security find-generic-password -a "$USER" -s "claude-mcp-reddit-client-secret" -w 2>/dev/null) || {
  echo "[reddit-mcp-launcher] Keychain entry 'claude-mcp-reddit-client-secret' not found." >&2
  echo "[reddit-mcp-launcher] Run: ~/claude-hq/scripts/mcp-migrate-to-keychain.sh" >&2
  exit 1
}

export REDDIT_CLIENT_SECRET="$SECRET"
# REDDIT_CLIENT_ID is passed through from the desktop config env block
: "${REDDIT_CLIENT_ID:?REDDIT_CLIENT_ID must be set in claude_desktop_config.json}"

exec /Library/Frameworks/Python.framework/Versions/3.13/bin/uv \
  --directory /Users/sunil_rajput/reddit-mcp \
  run server.py
