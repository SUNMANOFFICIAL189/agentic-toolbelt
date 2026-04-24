#!/usr/bin/env bash
# HQ Watchdog — hook installer/uninstaller
#
# Installs:
#   1. post-commit hook on ~/claude-hq/.git/hooks/post-commit
#   2. Session-end Stop hook in ~/claude-hq/.claude/settings.json
#   3. Cron entry for 08:00 daily digest (opt-in; prompts before touching crontab)
#
# Idempotent — safe to re-run. Uninstall with --uninstall.

set -euo pipefail

WATCHDOG="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HQ="$(cd "${WATCHDOG}/.." && pwd)"
GIT_HOOK="${CLAUDE_HQ}/.git/hooks/post-commit"
SETTINGS="${CLAUDE_HQ}/.claude/settings.json"

MODE="${1:-install}"
LAUNCHD_PLIST_SRC="${WATCHDOG}/com.claude-hq.watchdog.listener.plist"
LAUNCHD_PLIST_DST="${HOME}/Library/LaunchAgents/com.claude-hq.watchdog.listener.plist"

print_plain() {
    printf '%s\n' "$1"
}

install_listener() {
    mkdir -p "$(dirname "${LAUNCHD_PLIST_DST}")"
    # Copy (not symlink — launchd re-reads on load, symlink to a moved path would break)
    cp "${LAUNCHD_PLIST_SRC}" "${LAUNCHD_PLIST_DST}"

    # Unload if already loaded (idempotent)
    launchctl unload "${LAUNCHD_PLIST_DST}" 2>/dev/null || true
    if launchctl load "${LAUNCHD_PLIST_DST}" 2>&1; then
        print_plain "✓ Telegram listener installed and started"
        print_plain "  Polls Telegram every 30 seconds for commands from your chat"
        print_plain "  Logs: ${WATCHDOG}/listener.out.log and listener.err.log"
        print_plain "  Audit: ${WATCHDOG}/audit.log"
    else
        print_plain "❌ Failed to load launchd agent — check the error above"
        return 1
    fi
}

uninstall_listener() {
    if [[ -f "${LAUNCHD_PLIST_DST}" ]]; then
        launchctl unload "${LAUNCHD_PLIST_DST}" 2>/dev/null || true
        rm -f "${LAUNCHD_PLIST_DST}"
        print_plain "✓ Telegram listener uninstalled"
    else
        print_plain "ℹ No Telegram listener was installed"
    fi
}

install_git_hook() {
    if [[ -e "${GIT_HOOK}" ]] && [[ ! -L "${GIT_HOOK}" ]]; then
        print_plain "⚠ ${GIT_HOOK} already exists and is not a symlink."
        print_plain "  Backing it up to ${GIT_HOOK}.pre-watchdog"
        mv "${GIT_HOOK}" "${GIT_HOOK}.pre-watchdog"
    fi
    ln -sfn "${WATCHDOG}/hooks/post-commit" "${GIT_HOOK}"
    chmod +x "${WATCHDOG}/hooks/post-commit"
    print_plain "✓ post-commit hook installed at ${GIT_HOOK}"
}

install_session_hook() {
    mkdir -p "$(dirname "${SETTINGS}")"
    chmod +x "${WATCHDOG}/hooks/session-end.sh"

    # If settings.json exists and already references watchdog, skip
    if [[ -f "${SETTINGS}" ]] && grep -q "session-end.sh" "${SETTINGS}"; then
        print_plain "✓ session-end hook already registered in ${SETTINGS}"
        return
    fi

    # Append a minimal Stop hook. We don't rewrite existing settings — we
    # leave a clear note for manual merge if settings.json has other hooks.
    if [[ -f "${SETTINGS}" ]]; then
        print_plain "ℹ ${SETTINGS} exists. Add this Stop hook manually:"
        print_plain "    \"hooks\": { \"Stop\": [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"${WATCHDOG}/hooks/session-end.sh\" } ] } ] }"
    else
        cat > "${SETTINGS}" <<EOF
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "${WATCHDOG}/hooks/session-end.sh" }
        ]
      }
    ]
  }
}
EOF
        print_plain "✓ session-end Stop hook installed in ${SETTINGS}"
    fi
}

uninstall_git_hook() {
    if [[ -L "${GIT_HOOK}" ]]; then
        rm -f "${GIT_HOOK}"
        print_plain "✓ Removed post-commit hook"
    fi
    if [[ -e "${GIT_HOOK}.pre-watchdog" ]]; then
        mv "${GIT_HOOK}.pre-watchdog" "${GIT_HOOK}"
        print_plain "✓ Restored pre-watchdog git hook"
    fi
}

uninstall_session_hook() {
    if [[ -f "${SETTINGS}" ]] && grep -q "session-end.sh" "${SETTINGS}"; then
        print_plain "ℹ Remove the session-end.sh entry from ${SETTINGS} manually."
        print_plain "  (Not auto-removed to avoid corrupting other hook entries.)"
    fi
}

case "${MODE}" in
    install|"")
        print_plain "Installing HQ Watchdog hooks…"
        install_git_hook
        install_session_hook
        install_listener
        print_plain ""
        print_plain "Done. The watchdog will run:"
        print_plain "  • after every commit on claude-hq (post-commit hook)"
        print_plain "  • when a Claude Code session ends (Stop hook)"
        print_plain "  • every 30 seconds polling Telegram for commands (launchd agent)"
        print_plain ""
        print_plain "Test the pipe: python3 ${WATCHDOG}/telegram.py --self-test"
        print_plain "Try it: send 'help' to your HQ Watchdog bot on Telegram"
        print_plain "Disable temporarily: reply 'pause' on Telegram, or set WATCHDOG_ENABLED=false in ${WATCHDOG}/.env"
        ;;
    --listener|listener)
        install_listener
        ;;
    --listener-uninstall|listener-uninstall)
        uninstall_listener
        ;;
    --uninstall|uninstall)
        print_plain "Uninstalling HQ Watchdog hooks…"
        uninstall_git_hook
        uninstall_session_hook
        uninstall_listener
        print_plain ""
        print_plain "Done. The watchdog code is still on disk; delete watchdog/ to remove completely."
        ;;
    *)
        print_plain "Usage: $0 [install|--uninstall|--listener|--listener-uninstall]"
        exit 1
        ;;
esac
