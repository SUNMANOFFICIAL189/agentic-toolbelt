#!/usr/bin/env bash
# Model routing hook — PreToolUse handler for Agent dispatches.
# Doctrine: commander/MODEL_ROUTING.md. Implementation: lib/model-router.py.
#
# Invoked by Claude Code as a PreToolUse hook. Reads JSON from stdin.
# Always exits 0 — never blocks dispatches.

set -uo pipefail

HQ_ROOT="${HQ_ROOT:-$HOME/claude-hq}"
exec /usr/bin/env python3 "$HQ_ROOT/scripts/lib/model-router.py"
