#!/usr/bin/env bash
# memory-probe.sh — unified probe across HQ memory banks.
#
# Per Lesson 21: Before starting non-trivial work, sweep all memory banks
# with a query to surface prior work, decisions, parked items, and rules
# the task should respect. Output is structured for both human reading and
# for me (Claude) to skim and surface relevant hits to the user.
#
# Trust hierarchy (highest to lowest, mirrored in output order):
#   1. Vault Decision Log    — provenance-tagged architectural decisions
#   2. BACKLOG.md            — explicitly-parked work the user wants tracked
#   3. LESSONS.md            — preventive rules from past corrections
#   4. MemPalace             — semantic search across mined drawers
#   5. Hindsight             — past session summaries (if running)
#   6. (Graphify skipped     — stale until clean regen, see BACKLOG)
#
# Usage:
#   ~/claude-hq/scripts/memory-probe.sh "<query>"
#   mp "<query>"                                  # if you `alias mp=...` in shell rc
#
# Designed to be cheap (~5-10s, ~1-2KB output) and fail-soft. Any unreachable
# bank just prints "(unavailable)" rather than aborting the whole probe.

set -uo pipefail

QUERY="${1:?usage: memory-probe.sh \"<query>\"}"

# Helpers ---------------------------------------------------------------------

print_header() {
    echo
    echo "─── $1 ───"
}

# Build a forgiving regex from QUERY: spaces become "[- ]?" so "multi model"
# matches "multi-model" / "multimodel" / "multi model". Lowercase comparison.
QUERY_REGEX=$(python3 -c "
import re, sys
q = sys.argv[1].lower().strip()
parts = re.split(r'\s+', q)
print('[- ]?'.join(re.escape(p) for p in parts))
" "$QUERY")

# Case-insensitive regex grep with N lines of context. Returns 0 even on
# no-match so the script doesn't abort under set -e.
ctx_grep() {
    local file="$1"
    local before="${2:-1}"
    local after="${3:-2}"
    if [ -f "$file" ]; then
        grep -i -E -B "$before" -A "$after" -- "$QUERY_REGEX" "$file" 2>/dev/null | head -25 \
            || echo "  no match"
    else
        echo "  file not found: $file"
    fi
}

# 1. Vault Decision Log -------------------------------------------------------
print_header "decision log (highest trust)"
DECISION_LOG="$HOME/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/claude-hq/Decision Log.md"
ctx_grep "$DECISION_LOG" 1 3

# 2. BACKLOG.md ---------------------------------------------------------------
print_header "backlog (parked work)"
ctx_grep "$HOME/claude-hq/docs/BACKLOG.md" 0 2

# 3. LESSONS.md ---------------------------------------------------------------
print_header "lessons (preventive rules)"
ctx_grep "$HOME/claude-hq/commander/LESSONS.md" 0 3

# 4. MemPalace ----------------------------------------------------------------
print_header "mempalace (semantic search)"
if command -v mempalace >/dev/null 2>&1; then
    # Run with a soft timeout via a Python wrapper since macOS lacks coreutils timeout
    python3 - "$QUERY" <<'PY' 2>&1 | head -30 || echo "  (mempalace error)"
import subprocess, sys
q = sys.argv[1]
try:
    r = subprocess.run(["mempalace", "search", q], capture_output=True, text=True, timeout=15, check=False)
    if r.returncode == 0 and r.stdout.strip():
        print(r.stdout)
    elif r.returncode != 0:
        print(f"  (mempalace exit {r.returncode})")
    else:
        print("  no match")
except subprocess.TimeoutExpired:
    print("  (mempalace timeout)")
except Exception as e:
    print(f"  (mempalace error: {e})")
PY
else
    echo "  mempalace not installed"
fi

# 5. Hindsight ----------------------------------------------------------------
print_header "hindsight (past sessions)"
HC_BODY=$(
    curl -sf -m 3 \
        "http://localhost:8888/v1/default/banks/claude-sessions/memories?query=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$QUERY")" \
        2>/dev/null
)
if [ -n "$HC_BODY" ]; then
    echo "$HC_BODY" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    items = d.get('items', [])[:3]
    if not items:
        print('  no match')
    else:
        for i in items:
            content = (i.get('content') or '').strip().replace('\n', ' ')
            print(f'  • {content[:140]}{\"…\" if len(content) > 140 else \"\"}')
except Exception as e:
    print(f'  (parse error: {e})')
" 2>&1 || echo "  (parse error)"
else
    echo "  unavailable (server not running on localhost:8888)"
fi

# 6. Graphify -----------------------------------------------------------------
print_header "graphify"
echo "  skipped — graph stale (last regen 2026-04-21). See BACKLOG entry"
echo "  '2026-05-08 — graphify clean regen with repos/ excluded'."

# Footer ----------------------------------------------------------------------
echo
echo "(probe complete · trust hierarchy: decision log > backlog > lessons > mempalace > hindsight)"
