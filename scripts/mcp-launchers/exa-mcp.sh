#!/usr/bin/env bash
# Launcher for exa-mcp — fetches EXA_API_KEY from Keychain at spawn time.
# Pattern: per LESSONS.md rules 14-15, the secret never appears in
# claude_desktop_config.json. The config's env: {} stays empty; this launcher
# pulls the key fresh from Keychain on every MCP server start.
set -euo pipefail

SECRET=$(security find-generic-password -a "$USER" -s "claude-mcp-exa-api-key" -w 2>/dev/null) || {
  cat >&2 <<EOF
[exa-mcp-launcher] Keychain entry 'claude-mcp-exa-api-key' not found.

To set the key (one time):
  security add-generic-password -U -a "\$USER" -s claude-mcp-exa-api-key -w <YOUR_EXA_KEY>

Then restart Claude Desktop.
EOF
  exit 1
}

export EXA_API_KEY="$SECRET"
export PATH="/Users/sunil_rajput/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

exec npx -y exa-mcp-server
