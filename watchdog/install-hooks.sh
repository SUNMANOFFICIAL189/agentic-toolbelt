#!/usr/bin/env bash
# HQ Watchdog — hook installer/uninstaller
#
# Installs the watchdog's hooks into a target project (defaults to claude-hq):
#   1. post-commit hook in <project>/.git/hooks/post-commit
#   2. Session-end Stop hook in <project>/.claude/settings.json
#   3. (claude-hq only) launchd agent for Telegram listener
#
# Usage:
#   ./install-hooks.sh                          # install into claude-hq
#   ./install-hooks.sh install                  # same
#   ./install-hooks.sh install --project PATH   # install into PATH (e.g. PATS)
#   ./install-hooks.sh --uninstall              # remove from claude-hq
#   ./install-hooks.sh --uninstall --project PATH
#   ./install-hooks.sh --listener               # (re)install launchd agent
#   ./install-hooks.sh --listener-uninstall
#
# Idempotent — safe to re-run.

set -euo pipefail

WATCHDOG="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HQ="$(cd "${WATCHDOG}/.." && pwd)"
LAUNCHD_PLIST_SRC="${WATCHDOG}/com.claude-hq.watchdog.listener.plist"
LAUNCHD_PLIST_DST="${HOME}/Library/LaunchAgents/com.claude-hq.watchdog.listener.plist"

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------

MODE="install"
PROJECT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        install) MODE="install"; shift ;;
        --uninstall|uninstall) MODE="uninstall"; shift ;;
        --listener|listener) MODE="listener"; shift ;;
        --listener-uninstall|listener-uninstall) MODE="listener-uninstall"; shift ;;
        --project)
            shift
            [[ $# -gt 0 ]] || { echo "❌ --project requires a path"; exit 1; }
            PROJECT="$1"
            shift
            ;;
        -h|--help)
            sed -n '2,21p' "$0"
            exit 0
            ;;
        *)
            echo "❌ Unknown argument: $1"
            echo "Usage: $0 [install|--uninstall|--listener|--listener-uninstall] [--project PATH]"
            exit 1
            ;;
    esac
done

# Default project = claude-hq
if [[ -z "${PROJECT}" ]]; then
    PROJECT="${CLAUDE_HQ}"
fi

# Resolve project to absolute path (handles ~, relative paths)
PROJECT="$(cd "${PROJECT}" 2>/dev/null && pwd || echo "${PROJECT}")"

if [[ ! -d "${PROJECT}" ]]; then
    echo "❌ Project directory does not exist: ${PROJECT}"
    exit 1
fi

if [[ ! -d "${PROJECT}/.git" ]]; then
    echo "⚠ ${PROJECT} is not a git repo — post-commit hook will be skipped."
fi

GIT_HOOK="${PROJECT}/.git/hooks/post-commit"
SETTINGS="${PROJECT}/.claude/settings.json"
PROJECTS_JSON="${WATCHDOG}/projects.json"
PROJECT_NAME="$(basename "${PROJECT}")"
IS_CLAUDE_HQ=0
[[ "${PROJECT}" == "${CLAUDE_HQ}" ]] && IS_CLAUDE_HQ=1

print_plain() {
    printf '%s\n' "$1"
}

# -----------------------------------------------------------------------------
# Listener (launchd, claude-hq only — runs once globally)
# -----------------------------------------------------------------------------

install_listener() {
    mkdir -p "$(dirname "${LAUNCHD_PLIST_DST}")"
    cp "${LAUNCHD_PLIST_SRC}" "${LAUNCHD_PLIST_DST}"
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

# -----------------------------------------------------------------------------
# Per-project: post-commit hook
# -----------------------------------------------------------------------------

# Generate a project-specific post-commit hook with absolute paths embedded.
# Avoids symlink resolution issues when installed across project boundaries.
# The hook passes --project NAME so the watchdog scopes assessment to this
# project (avoids re-scoring everything on every commit) and so the structure
# is B-ready (future per-project watchdogs would swap binary path, not args).
write_post_commit_hook() {
    local target="$1"
    local project_dir="$2"
    local project_name="$3"
    cat > "${target}" <<HOOK_EOF
#!/usr/bin/env bash
# HQ Watchdog — post-commit hook
# Installed by: ${WATCHDOG}/install-hooks.sh
# Project: ${project_dir} (name: ${project_name})
#
# Calls the watchdog scoring engine after every commit. Never blocks.
set -u

WATCHDOG_DIR="${WATCHDOG}"
PROJECT_DIR="${project_dir}"
PROJECT_NAME="${project_name}"
LOG="\${WATCHDOG_DIR}/hook.log"
CHAINED="\${PROJECT_DIR}/.git/hooks/post-commit.pre-watchdog"

if [[ -f "\${WATCHDOG_DIR}/.env" ]] && grep -q "^WATCHDOG_ENABLED=false" "\${WATCHDOG_DIR}/.env" 2>/dev/null; then
    [[ -x "\${CHAINED}" ]] && "\${CHAINED}" || true
    exit 0
fi

if [[ -x "\${CHAINED}" ]]; then
    "\${CHAINED}" || true
fi

(
    python3 "\${WATCHDOG_DIR}/watchdog.py" --all --project "\${PROJECT_NAME}" \\
        >> "\${LOG}" 2>&1 || true
) >/dev/null 2>&1 &

exit 0
HOOK_EOF
    chmod +x "${target}"
}

install_git_hook() {
    if [[ ! -d "${PROJECT}/.git" ]]; then
        print_plain "ℹ Skipping post-commit hook (no .git in ${PROJECT})"
        return
    fi
    mkdir -p "${PROJECT}/.git/hooks"

    if [[ -e "${GIT_HOOK}" ]] && [[ ! -L "${GIT_HOOK}" ]]; then
        if ! grep -q "HQ Watchdog" "${GIT_HOOK}" 2>/dev/null; then
            print_plain "⚠ ${GIT_HOOK} exists and is not a watchdog hook."
            print_plain "  Backing it up to ${GIT_HOOK}.pre-watchdog"
            mv "${GIT_HOOK}" "${GIT_HOOK}.pre-watchdog"
        fi
    elif [[ -L "${GIT_HOOK}" ]]; then
        rm -f "${GIT_HOOK}"
    fi

    write_post_commit_hook "${GIT_HOOK}" "${PROJECT}" "${PROJECT_NAME}"
    print_plain "✓ post-commit hook installed at ${GIT_HOOK} (project=${PROJECT_NAME})"
}

# -----------------------------------------------------------------------------
# Per-project: register in projects.json (Option C / B-readiness #2)
# -----------------------------------------------------------------------------

register_project() {
    if [[ ! -f "${PROJECTS_JSON}" ]]; then
        print_plain "⚠ ${PROJECTS_JSON} not found — skipping registration."
        print_plain "  The watchdog will fall back to claude-hq-only ingestion."
        return
    fi
    # Idempotent JSON edit via Python so we don't add duplicates and don't
    # corrupt the file with a sed regex.
    python3 - "${PROJECTS_JSON}" "${PROJECT_NAME}" "${PROJECT}" <<'PY'
import json, sys
from datetime import date
projects_json, name, repo_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(projects_json) as f:
    data = json.load(f)
projects = data.get("projects", [])
existing = next((p for p in projects if p.get("name") == name), None)
if existing:
    existing["repo_path"] = repo_path
    print(f"  (project '{name}' already registered, repo_path refreshed)")
else:
    projects.append({
        "name": name,
        "repo_path": repo_path,
        "lessons_path": None,
        "added": date.today().isoformat(),
        "notes": "Registered automatically by install-hooks.sh.",
    })
    print(f"  (project '{name}' registered)")
data["projects"] = projects
data["last_updated"] = date.today().isoformat()
with open(projects_json, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
    print_plain "✓ project registered in projects.json"
}

unregister_project() {
    if [[ ! -f "${PROJECTS_JSON}" ]]; then
        return
    fi
    if [[ "${IS_CLAUDE_HQ}" -eq 1 ]]; then
        # Don't unregister claude-hq — it's the default project that the
        # watchdog needs to keep working (lessons reading, fallback).
        print_plain "ℹ Skipping unregister — claude-hq is the default project."
        return
    fi
    python3 - "${PROJECTS_JSON}" "${PROJECT_NAME}" <<'PY'
import json, sys
from datetime import date
projects_json, name = sys.argv[1], sys.argv[2]
with open(projects_json) as f:
    data = json.load(f)
projects = data.get("projects", [])
before = len(projects)
projects = [p for p in projects if p.get("name") != name]
data["projects"] = projects
data["last_updated"] = date.today().isoformat()
with open(projects_json, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print(f"  (removed {before - len(projects)} entry/entries for '{name}')")
PY
    print_plain "✓ project removed from projects.json"
}

uninstall_git_hook() {
    if [[ -f "${GIT_HOOK}" ]] && grep -q "HQ Watchdog" "${GIT_HOOK}" 2>/dev/null; then
        rm -f "${GIT_HOOK}"
        print_plain "✓ Removed post-commit hook from ${GIT_HOOK}"
    elif [[ -L "${GIT_HOOK}" ]]; then
        rm -f "${GIT_HOOK}"
        print_plain "✓ Removed post-commit symlink"
    fi
    if [[ -e "${GIT_HOOK}.pre-watchdog" ]]; then
        mv "${GIT_HOOK}.pre-watchdog" "${GIT_HOOK}"
        print_plain "✓ Restored pre-watchdog git hook"
    fi
}

# -----------------------------------------------------------------------------
# Per-project: session-end Stop hook in .claude/settings.json
# -----------------------------------------------------------------------------

install_session_hook() {
    mkdir -p "$(dirname "${SETTINGS}")"
    chmod +x "${WATCHDOG}/hooks/session-end.sh"

    if [[ -f "${SETTINGS}" ]] && grep -q "session-end.sh" "${SETTINGS}"; then
        print_plain "✓ session-end hook already registered in ${SETTINGS}"
        return
    fi

    if [[ -f "${SETTINGS}" ]]; then
        print_plain "ℹ ${SETTINGS} exists with other settings."
        print_plain "  Add this Stop hook manually inside the \"hooks\" object:"
        print_plain "    \"Stop\": [ { \"hooks\": [ { \"type\": \"command\", \"command\": \"${WATCHDOG}/hooks/session-end.sh\" } ] } ]"
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

uninstall_session_hook() {
    if [[ -f "${SETTINGS}" ]] && grep -q "session-end.sh" "${SETTINGS}"; then
        print_plain "ℹ Remove the session-end.sh entry from ${SETTINGS} manually."
        print_plain "  (Not auto-removed to avoid corrupting other hook entries.)"
    fi
}

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------

case "${MODE}" in
    install)
        print_plain "Installing HQ Watchdog hooks into: ${PROJECT}"
        register_project
        install_git_hook
        install_session_hook
        if [[ "${IS_CLAUDE_HQ}" -eq 1 ]]; then
            install_listener
        else
            print_plain "ℹ Listener is global — already running from claude-hq install (skipped)."
        fi
        print_plain ""
        print_plain "Done. The watchdog will run:"
        print_plain "  • after every commit on ${PROJECT} (post-commit hook)"
        print_plain "  • when a Claude Code session ends in ${PROJECT} (Stop hook)"
        if [[ "${IS_CLAUDE_HQ}" -eq 1 ]]; then
            print_plain "  • every 30 seconds polling Telegram for commands (launchd agent)"
        fi
        print_plain ""
        print_plain "Disable temporarily: reply 'pause' on Telegram, or set WATCHDOG_ENABLED=false in ${WATCHDOG}/.env"
        ;;
    uninstall)
        print_plain "Uninstalling HQ Watchdog hooks from: ${PROJECT}"
        uninstall_git_hook
        uninstall_session_hook
        unregister_project
        if [[ "${IS_CLAUDE_HQ}" -eq 1 ]]; then
            uninstall_listener
        fi
        print_plain ""
        print_plain "Done. The watchdog code is still on disk; delete ${WATCHDOG} to remove completely."
        ;;
    listener)
        install_listener
        ;;
    listener-uninstall)
        uninstall_listener
        ;;
esac
