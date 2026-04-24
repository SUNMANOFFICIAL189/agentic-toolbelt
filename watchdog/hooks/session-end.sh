#!/usr/bin/env bash
# HQ Watchdog — session-end hook
#
# Registered via .claude/settings.json as a Stop hook. Claude Code fires this
# when a session ends. We re-ingest session files and re-score quietly.
#
# Installed by: watchdog/install-hooks.sh
set -u

CLAUDE_HQ="$(cd "$(dirname "$0")/../.." && pwd)"
WATCHDOG="${CLAUDE_HQ}/watchdog"
LOG="${WATCHDOG}/hook.log"

# Bail if disabled
if [[ -f "${WATCHDOG}/.env" ]] && grep -q "^WATCHDOG_ENABLED=false" "${WATCHDOG}/.env" 2>/dev/null; then
    exit 0
fi

(
    python3 "${WATCHDOG}/watchdog.py" --all \
        >> "${LOG}" 2>&1 || true
) >/dev/null 2>&1 &

exit 0
