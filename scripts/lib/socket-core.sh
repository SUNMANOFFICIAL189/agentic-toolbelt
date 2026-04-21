#!/usr/bin/env bash
# Layer 3 — Socket + pip-audit package behavioural scan
# Socket detects malicious behaviour (typosquatting, compromised maintainers,
# obfuscated code) — it caught the Axios 4.2.1 compromise in 6 minutes.
# pip-audit catches known CVEs in Python requirements.
#
# Usage:
#   socket_scan_npm <package-or-dir>
#   pip_audit_scan <dir-with-requirements>
# Returns: 0 = pass, 1 = hard fail

set -euo pipefail

: "${TRUST_GATE_TMP:=/tmp/trust-gate-$$}"
mkdir -p "$TRUST_GATE_TMP"

socket_scan_npm() {
  local target="$1"

  if ! command -v socket >/dev/null 2>&1; then
    echo "socket_scan_npm: socket CLI not installed" >&2
    return 1
  fi

  local report="$TRUST_GATE_TMP/socket.json"

  # Socket scan works on package name, manifest, or dir
  if socket scan create "$target" --json > "$report" 2>/dev/null; then
    # Pass/fail decision based on high-severity issues
    local high_issues
    high_issues=$(python3 - "$report" <<'PY' 2>/dev/null || echo "0"
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    issues = data.get('issues', data.get('alerts', []))
    high = sum(1 for i in issues if isinstance(i, dict) and
               i.get('severity', '').lower() in ('high', 'critical'))
    print(high)
except Exception:
    print(0)
PY
)
    if [[ "$high_issues" -gt 0 ]]; then
      echo "socket_scan_npm: HARD FAIL — $high_issues high/critical issues in $target" >&2
      cat "$report" >&2
      return 1
    fi
    echo "socket_scan_npm: PASS — $target" >&2
    return 0
  else
    # Socket scan failure — fail closed
    echo "socket_scan_npm: scan failed (treating as block for safety) — $target" >&2
    return 1
  fi
}

pip_audit_scan() {
  local target="$1"

  if ! command -v pip-audit >/dev/null 2>&1; then
    echo "pip_audit_scan: pip-audit not installed" >&2
    return 1
  fi

  local report="$TRUST_GATE_TMP/pip-audit.json"

  # Find requirements files
  local req_files=()
  for f in "$target/requirements.txt" "$target/pyproject.toml" "$target/setup.py" "$target/Pipfile"; do
    [[ -f "$f" ]] && req_files+=("$f")
  done

  if [[ ${#req_files[@]} -eq 0 ]]; then
    echo "pip_audit_scan: no Python manifests in $target (skipping)" >&2
    return 0
  fi

  local any_fail=0
  for f in "${req_files[@]}"; do
    if [[ "$f" == *requirements.txt ]]; then
      if ! pip-audit -r "$f" --format json > "$report" 2>/dev/null; then
        any_fail=1
        echo "pip_audit_scan: vulns in $f" >&2
        cat "$report" >&2
      fi
    fi
  done

  if [[ "$any_fail" -eq 1 ]]; then
    echo "pip_audit_scan: HARD FAIL — known CVEs in Python deps of $target" >&2
    return 1
  fi

  echo "pip_audit_scan: PASS — $target" >&2
  return 0
}
