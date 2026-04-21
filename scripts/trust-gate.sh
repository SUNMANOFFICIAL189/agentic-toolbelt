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

# Inline override detection — user prefixes command with HQ_TRUST_OVERRIDE=1.
# Needed because PreToolUse hooks run before the command executes; env vars
# set on the command line never reach this process. Detect in the command string.
OVERRIDE_INLINE=0
if [[ "$CMD" =~ (^|[[:space:]]|\')HQ_TRUST_OVERRIDE=1([[:space:]]|$) ]]; then
  OVERRIDE_INLINE=1
fi

# Extract the real URL for `git clone` by tokenising and skipping flags.
# The old regex failed on `--branch NAME URL` because it treated the branch
# name as the URL. Use shlex via python3 for robust parsing.
parse_git_clone_url() {
  CMD="$CMD" python3 - <<'PY'
import os, shlex, sys
cmd = os.environ.get('CMD', '')
try:
    toks = shlex.split(cmd, posix=True)
except ValueError:
    sys.exit(1)
# Walk to first "git clone"
start = None
for i in range(len(toks) - 1):
    if toks[i] == 'git' and toks[i+1] == 'clone':
        start = i + 2
        break
if start is None:
    sys.exit(1)
# Flags that take a value as the next token
FLAGS_WITH_VAL = {
    '-b', '--branch', '--depth', '--shallow-since', '--shallow-exclude',
    '--reference', '--reference-if-able', '--origin', '-o', '--upload-pack',
    '--template', '--separate-git-dir', '-c', '-j', '--jobs', '--filter',
    '--bundle-uri', '--server-option', '--recurse-submodules',
}
skip = False
for tok in toks[start:]:
    if skip:
        skip = False
        continue
    if tok in FLAGS_WITH_VAL:
        skip = True
        continue
    if tok.startswith('-'):
        # flag (possibly --foo=bar) — skip
        continue
    print(tok)
    sys.exit(0)
sys.exit(1)
PY
}

# Extract install-style commands worth gating
TARGET=""
GATE_TIER=""

# git clone — URL extracted via tokenised parser (handles --branch, --depth, etc.)
if [[ "$CMD" =~ git[[:space:]]+clone([[:space:]]|$) ]]; then
  set +e
  TARGET="$(parse_git_clone_url)"
  set -e
  [[ -z "$TARGET" ]] && { log "git clone but no URL extracted — allowing"; exit 0; }
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
  [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" || "$OVERRIDE_INLINE" == "1" ]] && { log "override used on Tier C for $TARGET"; exit 0; }
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
    [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" || "$OVERRIDE_INLINE" == "1" ]] && { log "override used on cooling-off for $TARGET"; exit 0; }
    exit 2
    ;;
  2)
    cat >&2 <<EOF
Trust Gate: UNKNOWN AUTHOR — '$TARGET'
Recommend routing through Tier C (/scout or skill-install.sh).
To proceed anyway (acknowledges risk), prefix: HQ_TRUST_OVERRIDE=1
EOF
    [[ "${HQ_TRUST_OVERRIDE:-0}" == "1" || "$OVERRIDE_INLINE" == "1" ]] && { log "override used on unknown author for $TARGET"; exit 0; }
    exit 2
    ;;
esac

exit 0
