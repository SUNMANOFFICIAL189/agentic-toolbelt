#!/usr/bin/env bash
# Layer 2 — Prompt-injection + hardcoded-secret scan
# Grep-based static analysis. Catches known injection patterns in SKILL.md/README.md
# and common credential leaks (Snyk Feb 2026 data: 10.9% of skills have hardcoded secrets).
#
# Usage: secret_scan <directory>
# Returns: 0 = pass, 1 = hard fail, 2 = warnings

set -euo pipefail

: "${TRUST_GATE_TMP:=/tmp/trust-gate-$$}"
mkdir -p "$TRUST_GATE_TMP"

# Prompt-injection markers seen across ToxicSkills study + OWASP Agentic Skills Top 10
# These are patterns that attempt to override agent instructions via skill markdown
INJECTION_PATTERNS=(
  'ignore (all |previous |prior )?(above |earlier )?(instructions|prompts|rules)'
  'disregard (the |all |any )?(above|previous|prior|system)'
  'you are now (?:a |an )?[a-z]{3,}'
  'new (system |primary )?(prompt|instructions|rules)'
  'SYSTEM:[[:space:]]*you (?:must|will|should)'
  '\[\[INST\]\]|<\|im_start\|>'
  'jailbreak|DAN mode|developer mode'
  'exfiltrate|keylog|backdoor'
)

# Third-party content fetchers — 9% of skills.sh top-100 do this (red flag per Lakera)
FETCH_PATTERNS=(
  'curl[[:space:]]+[^|]*\|[[:space:]]*(bash|sh|zsh|python)'
  'wget[[:space:]]+[^|]*\|[[:space:]]*(bash|sh|zsh|python)'
  'eval[[:space:]]*\([[:space:]]*(requests|urllib|fetch)'
  'subprocess\..*shell=True'
)

# Hardcoded secret patterns — same as trufflehog/gitleaks baseline
SECRET_PATTERNS=(
  'sk-[a-zA-Z0-9]{20,}'                                      # OpenAI
  'sk-ant-[a-zA-Z0-9\-_]{20,}'                               # Anthropic
  'ghp_[a-zA-Z0-9]{30,}'                                     # GitHub PAT
  'gho_[a-zA-Z0-9]{30,}'                                     # GitHub OAuth
  'AKIA[0-9A-Z]{16}'                                         # AWS access key
  'AIza[0-9A-Za-z\-_]{35}'                                   # Google API
  'xox[baprs]-[0-9a-zA-Z\-]{10,}'                            # Slack
  '-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----'         # Private keys
)

secret_scan() {
  local target="$1"

  if [[ ! -d "$target" && ! -f "$target" ]]; then
    echo "secret_scan: target not found: $target" >&2
    return 1
  fi

  local report="$TRUST_GATE_TMP/secret-scan.txt"
  : > "$report"
  local hits=0

  # Scan markdown + config files for prompt injection
  for p in "${INJECTION_PATTERNS[@]}"; do
    if grep -r -l -I -i -E "$p" --include='*.md' --include='*.txt' --include='*.json' --include='*.yaml' --include='*.yml' "$target" 2>/dev/null | head -5 > /tmp/__hits.$$; then
      if [[ -s /tmp/__hits.$$ ]]; then
        echo "[PROMPT_INJECTION] pattern: $p" >> "$report"
        sed 's/^/  -> /' /tmp/__hits.$$ >> "$report"
        hits=$((hits + 1))
      fi
    fi
  done
  rm -f /tmp/__hits.$$

  # Scan for third-party fetchers (executable code only)
  for p in "${FETCH_PATTERNS[@]}"; do
    if grep -r -l -I -E "$p" --include='*.sh' --include='*.py' --include='*.js' --include='*.ts' --include='*.md' "$target" 2>/dev/null | head -5 > /tmp/__hits.$$; then
      if [[ -s /tmp/__hits.$$ ]]; then
        echo "[THIRD_PARTY_FETCHER] pattern: $p" >> "$report"
        sed 's/^/  -> /' /tmp/__hits.$$ >> "$report"
        hits=$((hits + 1))
      fi
    fi
  done
  rm -f /tmp/__hits.$$

  # Scan for hardcoded secrets (all file types)
  for p in "${SECRET_PATTERNS[@]}"; do
    if grep -r -l -I -E "$p" "$target" 2>/dev/null | head -5 > /tmp/__hits.$$; then
      if [[ -s /tmp/__hits.$$ ]]; then
        echo "[HARDCODED_SECRET] pattern type matched" >> "$report"
        sed 's/^/  -> /' /tmp/__hits.$$ >> "$report"
        hits=$((hits + 1))
      fi
    fi
  done
  rm -f /tmp/__hits.$$

  if [[ "$hits" -gt 0 ]]; then
    echo "secret_scan: HARD FAIL — $hits suspicious patterns in $target" >&2
    cat "$report" >&2
    return 1
  fi

  echo "secret_scan: PASS — no injection/secret patterns in $target" >&2
  return 0
}
