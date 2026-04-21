#!/usr/bin/env bash
# Skill Install — Tier C full pipeline
# For skills.sh discoveries and any install from an unknown author.
# Runs all 4 layers + reputation check before anything touches ~/.claude/skills/.
#
# Usage: skill-install.sh <owner/repo@skill> [--scope project|global]
# Default scope: project (promote to global manually after 2+ uses).

set -euo pipefail

HQ_ROOT="${HQ_ROOT:-/Users/sunil_rajput/claude-hq}"
LIB="$HQ_ROOT/scripts/lib"
LOG="$HQ_ROOT/scripts/.trust-gate.log"

source "$LIB/advisory-check.sh"
source "$LIB/magika-core.sh"
source "$LIB/secret-scan.sh"
source "$LIB/socket-core.sh"

log() { echo "[skill-install $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

SKILL_REF="${1:-}"
SCOPE="project"
if [[ "${2:-}" == "--scope" ]]; then
  SCOPE="${3:-project}"
fi

if [[ -z "$SKILL_REF" ]]; then
  cat >&2 <<EOF
Usage: skill-install.sh <owner/repo@skill> [--scope project|global]
Example: skill-install.sh trailofbits/skills@threat-modeling --scope global
EOF
  exit 1
fi

log "START $SKILL_REF scope=$SCOPE"

# -------- Layer 0.5: Advisory / incident ledger --------
set +e
advisory_check "$SKILL_REF"
adv_rc=$?
set -e

if [[ "$adv_rc" == "1" ]]; then
  log "BLOCK: cooling-off active for $SKILL_REF"
  exit 1
fi

# Allowlisted authors still go through file-content scan — we never fully skip Tier C
# for skills.sh content, because marketplace install counts are a weak signal
# (Snyk Feb 2026: 13.4% of catalog has critical issues regardless of author).

# -------- Fetch to staging dir (not yet installed) --------
STAGING="/tmp/skill-staging-$$"
mkdir -p "$STAGING"
trap 'rm -rf "$STAGING"' EXIT

OWNER_REPO="${SKILL_REF%@*}"
SKILL_NAME="${SKILL_REF##*@}"

log "fetching $OWNER_REPO into $STAGING"

# Clone from GitHub
if ! git clone --depth 1 "https://github.com/$OWNER_REPO.git" "$STAGING/src" 2>/dev/null; then
  log "ERROR: git clone failed for $OWNER_REPO"
  exit 1
fi

# -------- Layer 1: Magika --------
export TRUST_GATE_TMP="$STAGING/reports"
mkdir -p "$TRUST_GATE_TMP"

set +e
magika_scan "$STAGING/src"
magika_rc=$?
set -e

if [[ "$magika_rc" != "0" ]]; then
  log "BLOCK: Magika mismatch in $SKILL_REF"
  echo "See $TRUST_GATE_TMP for full report." >&2
  exit 1
fi

# -------- Layer 2: Secret + prompt-injection scan --------
set +e
secret_scan "$STAGING/src"
secret_rc=$?
set -e

if [[ "$secret_rc" != "0" ]]; then
  log "BLOCK: secret/injection pattern in $SKILL_REF"
  exit 1
fi

# -------- Layer 3: Socket / pip-audit if package manifests present --------
if [[ -f "$STAGING/src/package.json" ]]; then
  set +e
  socket_scan_npm "$STAGING/src"
  socket_rc=$?
  set -e
  if [[ "$socket_rc" != "0" ]]; then
    log "BLOCK: Socket flagged npm behaviour in $SKILL_REF"
    exit 1
  fi
fi

if [[ -f "$STAGING/src/requirements.txt" || -f "$STAGING/src/pyproject.toml" ]]; then
  set +e
  pip_audit_scan "$STAGING/src"
  py_rc=$?
  set -e
  if [[ "$py_rc" != "0" ]]; then
    log "BLOCK: pip-audit flagged Python CVEs in $SKILL_REF"
    exit 1
  fi
fi

# -------- Layer 4: Reputation (weak signal only) --------
# Skills.sh install count threshold — 10K auto-pass, 1-10K warn, <1K manual
# (Thresholds per LESSONS.md; counts are tie-breakers, not proof.)
log "reputation check skipped (install count via skills.sh API not yet wired — v2 TODO)"

# -------- Install --------
if [[ "$SCOPE" == "global" ]]; then
  TARGET_DIR="$HOME/.claude/skills"
else
  TARGET_DIR=".claude/skills"
fi

mkdir -p "$TARGET_DIR"

# The staging dir has the whole repo — copy just the named skill
# Skills.sh convention: skill dir is at <repo-root>/<skill-name>/ or <repo-root>/
if [[ -d "$STAGING/src/$SKILL_NAME" ]]; then
  cp -R "$STAGING/src/$SKILL_NAME" "$TARGET_DIR/"
elif [[ -f "$STAGING/src/SKILL.md" ]]; then
  # Single-skill repo
  cp -R "$STAGING/src" "$TARGET_DIR/$SKILL_NAME"
else
  log "ERROR: could not locate skill '$SKILL_NAME' in $OWNER_REPO"
  exit 1
fi

log "INSTALLED $SKILL_REF → $TARGET_DIR/$SKILL_NAME (scope=$SCOPE)"
echo ""
echo "✅ Installed: $SKILL_REF"
echo "   Scope:    $SCOPE ($TARGET_DIR/$SKILL_NAME)"
echo "   Layers:   advisory=$adv_rc magika=$magika_rc secret=$secret_rc"
echo ""
echo "Reminder: first real use happens in a project — promote to global after 2+ clean uses."
