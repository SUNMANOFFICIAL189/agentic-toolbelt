#!/usr/bin/env bash
# One-time migration: move plaintext secrets from claude_desktop_config.json
# into macOS Keychain, then rewrite the config to point at per-MCP launcher
# scripts that fetch the secret at spawn time.
#
# Idempotent: safe to run multiple times. Each run re-stores current values
# (using -U) and re-writes the config.

set -euo pipefail

CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
BACKUP_DIR="$HOME/claude-hq/.credentials"
LAUNCHER_DIR="$HOME/claude-hq/scripts/mcp-launchers"
TS=$(date +%Y%m%d-%H%M%S)

if [[ ! -f "$CFG" ]]; then
  echo "[fatal] claude_desktop_config.json not found at $CFG" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR" "$LAUNCHER_DIR"
chmod 700 "$BACKUP_DIR"

BACKUP="$BACKUP_DIR/claude_desktop_config.pre-keychain.$TS.json"
cp "$CFG" "$BACKUP"
chmod 600 "$BACKUP"
echo "[backup] $BACKUP"

# Use Python (always available on macOS) for JSON ops + Keychain calls.
# Secrets never leave the Python process (no echo, no logging, no stdout).
python3 - "$CFG" "$LAUNCHER_DIR" <<'PY'
import json, subprocess, sys, os

cfg_path, launcher_dir = sys.argv[1], sys.argv[2]
user = os.environ["USER"]

with open(cfg_path) as f:
    cfg = json.load(f)

servers = cfg.get("mcpServers", {})

# (server_key, env_var_name, keychain_service)
mapping = [
    ("reddit",             "REDDIT_CLIENT_SECRET",        "claude-mcp-reddit-client-secret"),
    ("claude-code-bridge", "ANTHROPIC_API_KEY",           "claude-mcp-claude-code-bridge-api-key"),
    ("gemini-bridge",      "GEMINI_API_KEY",              "claude-mcp-gemini-bridge-api-key"),
    ("github",             "GITHUB_PERSONAL_ACCESS_TOKEN", "claude-mcp-github-pat"),
]

for srv, env_var, svc in mapping:
    env = servers.get(srv, {}).get("env", {}) or {}
    val = env.get(env_var)
    if not val:
        print(f"[skip] {svc} — {srv}.{env_var} not present")
        continue
    # security add-generic-password: -U update, -a account, -s service, -w password
    # Password passes as CLI arg (brief local ps exposure — acceptable tradeoff).
    subprocess.run(
        ["security", "add-generic-password", "-U", "-a", user, "-s", svc, "-w", val],
        check=True, capture_output=True,
    )
    print(f"[keychain] stored: {svc}")

# Rewrite each MCP to point at its launcher. Keep REDDIT_CLIENT_ID (public).
reddit_client_id = servers.get("reddit", {}).get("env", {}).get("REDDIT_CLIENT_ID", "")

servers["reddit"] = {
    "command": f"{launcher_dir}/reddit-mcp.sh",
    "args": [],
    "env": {"REDDIT_CLIENT_ID": reddit_client_id} if reddit_client_id else {},
}
servers["claude-code-bridge"] = {
    "command": f"{launcher_dir}/claude-code-bridge.sh",
    "args": [],
    "env": {},
}
servers["gemini-bridge"] = {
    "command": f"{launcher_dir}/gemini-bridge.sh",
    "args": [],
    "env": {},
}
servers["github"] = {
    "command": f"{launcher_dir}/github-mcp.sh",
    "args": [],
    "env": {},
}

cfg["mcpServers"] = servers

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

os.chmod(cfg_path, 0o600)
print(f"[config] rewritten: {cfg_path}")
PY

# Verify no secret-shaped patterns remain in the new config
if grep -E 'sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{35}' "$CFG" >/dev/null 2>&1; then
  echo "[warn] new config still contains secret-shaped patterns — inspect manually" >&2
  exit 2
fi
echo "[verify] config clean of known secret patterns"

echo
echo "Next steps:"
echo "  1. Restart Claude Desktop app to pick up new config"
echo "  2. MCPs will now launch via $LAUNCHER_DIR/*.sh"
echo "  3. Launchers retrieve secrets from Keychain at spawn time"
echo "  4. Backup of old config: $BACKUP (mode 600, gitignored)"
