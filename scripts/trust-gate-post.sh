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

# Parse tool output and command
parse_input() {
  python3 - <<'PY'
import json, os
try:
    data = json.loads(os.environ.get('INPUT', '{}'))
except Exception:
    data = {}
tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {})
command = tool_input.get('command', '') if isinstance(tool_input, dict) else ''
print('TOOL_NAME=' + json.dumps(tool_name))
print('CMD=' + json.dumps(command))
PY
}
eval "$(parse_input)"

[[ "$TOOL_NAME" != "Bash" ]] && exit 0

# Only scan after git clone commands
if [[ ! "$CMD" =~ git[[:space:]]+clone[[:space:]]+(--[a-z-]+[[:space:]]+)*([^[:space:]]+) ]]; then
  exit 0
fi

# Determine clone target dir (last token, or parsed from URL)
CLONE_TARGET=""
# If explicit dir given as last arg
tokens=($CMD)
if [[ ${#tokens[@]} -ge 4 && -d "${tokens[-1]}" ]]; then
  CLONE_TARGET="${tokens[-1]}"
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
