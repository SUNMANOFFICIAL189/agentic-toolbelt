#!/usr/bin/env bash
# Trust Gate — Tier B ambient hook entry point.
# Invoked by Claude Code PreToolUse hook on Bash commands.
# Reads hook JSON from stdin, decides whether to allow/block/ask the command.
#
# This hook is METADATA-ONLY (runs before clone/install). For post-clone file
# scanning, see trust-gate-post.sh. For full Tier C pipeline (skills.sh
# installs), see skill-install.sh.
#
# Exit codes:
#   0 — allow (stdout may contain JSON decision)
#   2 — block (stderr reason)

set -euo pipefail

HQ_ROOT="${HQ_ROOT:-/Users/sunil_rajput/claude-hq}"
LIB="$HQ_ROOT/scripts/lib"
LOG="$HQ_ROOT/scripts/.trust-gate.log"

# Source the layer libraries
# shellcheck source=lib/advisory-check.sh
source "$LIB/advisory-check.sh"

log() { echo "[trust-gate $(date +%H:%M:%S)] $*" >> "$LOG"; }

# Read hook input
INPUT="$(cat)"

# Parse tool name and command (requires python3 for JSON safety)
parse_hook_input() {
  python3 - <<PY
import json, sys, os
try:
    data = json.loads(os.environ.get('INPUT', '{}'))
except Exception:
    data = {}
tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {})
command = tool_input.get('command', '') if isinstance(tool_input, dict) else ''
# Print as env-safe lines
print('TOOL_NAME=' + json.dumps(tool_name))
print('CMD=' + json.dumps(command))
PY
}

export INPUT
eval "$(parse_hook_input)"

log "tool=$TOOL_NAME cmd=$CMD"

# Only act on Bash tool
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# Extract install-style commands worth gating
# Uses a single regex pass to detect the install patterns we care about.
TARGET=""
GATE_TIER=""

# git clone https://github.com/OWNER/REPO or git@github.com:OWNER/REPO
if [[ "$CMD" =~ git[[:space:]]+clone[[:space:]]+(--[a-z-]+[[:space:]]+)*([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[2]}"
  GATE_TIER="B"

# npx skills add OWNER/REPO@skill — always Tier C
elif [[ "$CMD" =~ npx[[:space:]]+(-y[[:space:]]+)?skills[[:space:]]+add[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[2]}"
  GATE_TIER="C"

# npm install -g PACKAGE or npm install https://...
elif [[ "$CMD" =~ npm[[:space:]]+install[[:space:]]+(-g[[:space:]]+|--global[[:space:]]+)?([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[2]}"
  GATE_TIER="B"

# pip install PACKAGE or pip install git+https://...
elif [[ "$CMD" =~ pip[[:space:]]+install[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[1]}"
  GATE_TIER="B"

# cargo install --git https://...
elif [[ "$CMD" =~ cargo[[:space:]]+install[[:space:]]+--git[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[1]}"
  GATE_TIER="B"

# pipx install PACKAGE
elif [[ "$CMD" =~ pipx[[:space:]]+install[[:space:]]+([^[:space:]]+) ]]; then
  TARGET="${BASH_REMATCH[1]}"
  GATE_TIER="B"

else
  # No install pattern — allow
  exit 0
fi

log "gate_tier=$GATE_TIER target=$TARGET"

# Tier C commands are ALWAYS routed through the full skill-install pipeline.
# We block here and point the user at /scout for the proper workflow.
if [[ "$GATE_TIER" == "C" ]]; then
  cat >&2 <<EOF
Trust Gate: Tier C install detected — '$TARGET'
skills.sh installs require the full Tier C pipeline (Magika + secret-scan + Socket + reputation).
Route this through: /scout "<description>"
Or bypass this gate for one command by prefixing: HQ_TRUST_OVERRIDE=1 <your command>
EOF
  [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" ]] && { log "override used on Tier C for $TARGET"; exit 0; }
  exit 2
fi

# Tier B — advisory check only (metadata, no files yet)
set +e
advisory_check "$TARGET" 2>> "$LOG"
rc=$?
set -e

case "$rc" in
  0)
    log "ALLOW (allowlisted author) — $TARGET"
    exit 0
    ;;
  1)
    cat >&2 <<EOF
Trust Gate: BLOCK — '$TARGET' is in active cooling-off period.
See: $HQ_ROOT/commander/INCIDENT_LEDGER.md
Override (not recommended): prefix command with HQ_TRUST_OVERRIDE=1
EOF
    [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" ]] && { log "override used on cooling-off for $TARGET"; exit 0; }
    exit 2
    ;;
  2)
    cat >&2 <<EOF
Trust Gate: UNKNOWN AUTHOR — '$TARGET'
Recommend routing through Tier C (/scout or skill-install.sh).
To proceed anyway (acknowledges risk), prefix: HQ_TRUST_OVERRIDE=1
EOF
    [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" ]] && { log "override used on unknown author for $TARGET"; exit 0; }
    exit 2
    ;;
esac

exit 0
