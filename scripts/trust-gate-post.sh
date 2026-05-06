#!/usr/bin/env bash
# Trust Gate — PostToolUse hook for git clone completion.
# After a clone succeeds (regardless of allowlist status), run Magika +
# secret-scan on the resulting directory and alert if anything surfaces.
# This catches the class where a trusted author's repo has been compromised
# between when we allowlisted them and when we cloned.
#
# Exit 0 always (post-hoc warnings only, no blocking).

set -euo pipefail

HQ_ROOT="${HQ_ROOT:-/Users/sunil_rajput/claude-hq}"
LIB="$HQ_ROOT/scripts/lib"
LOG="$HQ_ROOT/scripts/.trust-gate.log"

source "$LIB/magika-core.sh"
source "$LIB/secret-scan.sh"

log() { echo "[trust-gate-post $(date +%H:%M:%S)] $*" >> "$LOG"; }

INPUT="$(cat)"
export INPUT

# Parse tool output and command. Uses NUL-delimited raw values so bash never
# re-evaluates the contents — same fix as trust-gate.sh. See LESSONS rule 7.
parse_input() {
  python3 - <<'PY'
import json, os, sys
try:
    data = json.loads(os.environ.get('INPUT', '') or '{}')
except Exception:
    data = {}
tool_name = (data.get('tool_name') or '')
tool_input = data.get('tool_input') or {}
command = tool_input.get('command', '') if isinstance(tool_input, dict) else ''
sys.stdout.buffer.write(tool_name.encode('utf-8') + b'\x00')
sys.stdout.buffer.write(command.encode('utf-8') + b'\x00')
PY
}

TOOL_NAME=""
CMD=""
# Fail-open: if the read fails, hook continues with empty values and the
# non-Bash early exit short-circuits cleanly.
{ IFS= read -r -d '' TOOL_NAME && IFS= read -r -d '' CMD; } < <(parse_input) || true

[[ "$TOOL_NAME" != "Bash" ]] && exit 0

# Only scan after git clone commands
if [[ ! "$CMD" =~ git[[:space:]]+clone[[:space:]]+(--[a-z-]+[[:space:]]+)*([^[:space:]]+) ]]; then
  exit 0
fi

# Determine clone target dir (last token, or parsed from URL)
CLONE_TARGET=""
# If explicit dir given as last arg.
# NOTE: avoid ${tokens[-1]} — that's bash 4.2+ syntax. macOS /bin/bash is 3.2.
tokens=($CMD)
last_idx=$(( ${#tokens[@]} - 1 ))
if [[ ${#tokens[@]} -ge 4 && $last_idx -ge 0 && -d "${tokens[$last_idx]}" ]]; then
  CLONE_TARGET="${tokens[$last_idx]}"
else
  # Infer from URL: .../REPO.git or .../REPO
  url="${BASH_REMATCH[2]}"
  repo="${url##*/}"
  repo="${repo%.git}"
  # Check current working dir (hook inherits cwd)
  [[ -d "./$repo" ]] && CLONE_TARGET="./$repo"
fi

if [[ -z "$CLONE_TARGET" || ! -d "$CLONE_TARGET" ]]; then
  log "post-scan: could not locate cloned dir (cwd=$(pwd), cmd=$CMD)"
  exit 0
fi

log "post-scan target: $CLONE_TARGET"

export TRUST_GATE_TMP="/tmp/trust-gate-post-$$"
mkdir -p "$TRUST_GATE_TMP"

set +e
magika_scan "$CLONE_TARGET"
magika_rc=$?
secret_scan "$CLONE_TARGET"
secret_rc=$?
set -e

if [[ "$magika_rc" != "0" || "$secret_rc" != "0" ]]; then
  cat >&2 <<EOF
⚠️  Trust Gate post-clone scan FOUND ISSUES in: $CLONE_TARGET
   Magika: $([ $magika_rc -eq 0 ] && echo PASS || echo FAIL)
   Secret/injection scan: $([ $secret_rc -eq 0 ] && echo PASS || echo FAIL)
   See $TRUST_GATE_TMP/ for reports.
   Recommend: rm -rf "$CLONE_TARGET" until you've reviewed the findings.
EOF
  log "post-scan FAIL on $CLONE_TARGET (magika=$magika_rc secret=$secret_rc)"
else
  log "post-scan PASS on $CLONE_TARGET"
fi

# Non-blocking — exit 0 always for PostToolUse
exit 0
