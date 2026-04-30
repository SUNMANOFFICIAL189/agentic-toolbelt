#!/bin/bash
# Paperclip launcher — reads API keys from macOS Keychain at spawn time,
# exports them to Paperclip's process env, then exec's pnpm dev.
#
# Why this pattern (per HQ LESSONS Rule 14/15):
#   - Keys never live in plaintext config files
#   - Keys never appear in launchd plist EnvironmentVariables (which sit in /Library/LaunchAgents)
#   - Keys exist only in Keychain (encrypted at rest, login-required) and in this process's env
#   - `exec` replaces the launcher process so keys never persist beyond the running pnpm dev
set -euo pipefail

OPENROUTER_API_KEY=$(security find-generic-password -a "$USER" -s "claude-paperclip-openrouter" -w 2>/dev/null) || {
  echo "FATAL: Keychain entry 'claude-paperclip-openrouter' not found." >&2
  echo "Add via: security add-generic-password -U -a \"\$USER\" -s \"claude-paperclip-openrouter\" -w" >&2
  exit 1
}

GEMINI_API_KEY=$(security find-generic-password -a "$USER" -s "claude-paperclip-gemini" -w 2>/dev/null) || {
  echo "FATAL: Keychain entry 'claude-paperclip-gemini' not found." >&2
  echo "Add via: security add-generic-password -U -a \"\$USER\" -s \"claude-paperclip-gemini\" -w" >&2
  exit 1
}

export OPENROUTER_API_KEY GEMINI_API_KEY
export PATH="/Users/sunil_rajput/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cd /Users/sunil_rajput/projects/paperclip

exec /opt/homebrew/bin/pnpm dev
