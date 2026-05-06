#!/usr/bin/env bash
# HQ Watchdog — PATS warmup one-shot reminder.
#
# Triggered by ~/Library/LaunchAgents/com.claude-hq.watchdog.pats-warmup-reminder.plist
# at 2026-05-04 09:00 local. Runs the Python check, emails Sunil a plain-English
# status, then unloads + removes the launchd agent so it never fires again.
#
# Created: 2026-04-27 by request.

set -u

WATCHDOG="/Users/sunil_rajput/claude-hq/watchdog"
SCRIPT_DIR="${WATCHDOG}/scripts"
LOG="${WATCHDOG}/hook.log"
PLIST_LABEL="com.claude-hq.watchdog.pats-warmup-reminder"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"

{
    echo "$(date -Iseconds) [pats-warmup-reminder] firing"
} >> "${LOG}"

if python3 "${SCRIPT_DIR}/pats-warmup-reminder.py" >> "${LOG}" 2>&1; then
    echo "$(date -Iseconds) [pats-warmup-reminder] email sent — self-cleaning launchd agent" >> "${LOG}"

    # Self-clean: unload + delete the plist so this never fires again
    launchctl unload "${PLIST_PATH}" 2>/dev/null || true
    rm -f "${PLIST_PATH}"
else
    echo "$(date -Iseconds) [pats-warmup-reminder] email send failed — keeping launchd agent loaded for retry" >> "${LOG}"
    # Don't self-clean on failure. Sunil can investigate and retry manually.
fi

exit 0
