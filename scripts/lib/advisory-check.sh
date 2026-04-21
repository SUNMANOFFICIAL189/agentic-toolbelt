#!/usr/bin/env bash
# Layer 0.5 — Advisory + incident-ledger check
# Runs BEFORE Magika. Cheap metadata-only gate.
# Consults INCIDENT_LEDGER.md (vendor cooling-off periods) and the local
# author allowlist. Intended to run at PreToolUse time, when only URLs/metadata
# are available — no cloned files yet.
#
# Usage: advisory_check <url-or-owner/repo>
# Returns: 0 = allowlisted (auto-pass), 1 = in cooling-off (block),
#          2 = unknown (needs full Tier C)

set -euo pipefail

: "${HQ_ROOT:=/Users/sunil_rajput/claude-hq}"
: "${TRUST_GATE_TMP:=/tmp/trust-gate-$$}"
mkdir -p "$TRUST_GATE_TMP"

LEDGER="$HQ_ROOT/commander/INCIDENT_LEDGER.md"

# Author allowlist — trusted orgs that auto-pass on metadata alone.
# Deliberately excludes vercel/* until 2026-07-20 (see INCIDENT_LEDGER).
ALLOWLIST=(
  "SUNMANOFFICIAL189"
  "anthropics"
  "google"
  "microsoft"
  "thedotmack"
  "affaan-m"
  "trailofbits"
  "ChristopherKahler"
  "keshavsuki"
  "ruvnet"
)

# Parse owner from URL or owner/repo string
extract_owner() {
  local input="$1"
  # git@github.com:owner/repo.git
  if [[ "$input" =~ github\.com[:/]([^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  # owner/repo or owner/repo@skill
  if [[ "$input" =~ ^([a-zA-Z0-9_.-]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  echo ""
  return 1
}

# Check if an owner is in the INCIDENT_LEDGER cooling-off list
is_in_cooling_off() {
  local owner="$1"
  [[ -f "$LEDGER" ]] || return 1
  # Look for an entry like "COOLING_OFF: owner/... until YYYY-MM-DD"
  local today
  today="$(date +%Y-%m-%d)"
  local line
  while IFS= read -r line; do
    if [[ "$line" =~ ^COOLING_OFF:[[:space:]]+([^/]+)/.*until[[:space:]]+([0-9-]+) ]]; then
      local ledger_owner="${BASH_REMATCH[1]}"
      local until_date="${BASH_REMATCH[2]}"
      if [[ "$ledger_owner" == "$owner" && "$today" < "$until_date" ]]; then
        echo "COOLING_OFF: $owner (until $until_date)"
        return 0
      fi
    fi
  done < "$LEDGER"
  return 1
}

is_allowlisted() {
  local owner="$1"
  for a in "${ALLOWLIST[@]}"; do
    [[ "$a" == "$owner" ]] && return 0
  done
  return 1
}

advisory_check() {
  local input="$1"
  local owner
  owner="$(extract_owner "$input")"

  if [[ -z "$owner" ]]; then
    echo "advisory_check: could not parse owner from '$input' — treating as UNKNOWN" >&2
    return 2
  fi

  # Cooling-off period check always runs first — allowlist cannot override it
  if is_in_cooling_off "$owner"; then
    echo "advisory_check: BLOCK — $owner is in cooling-off (see INCIDENT_LEDGER.md)" >&2
    return 1
  fi

  if is_allowlisted "$owner"; then
    echo "advisory_check: ALLOWLISTED — $owner (metadata auto-pass, Magika still runs post-clone)" >&2
    return 0
  fi

  echo "advisory_check: UNKNOWN — $owner requires full Tier C pipeline" >&2
  return 2
}
