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

# Helper: grep a file with the regex but cap context lines to keep output tight
ctx_grep_short() {
    local file="$1"
    local before="${2:-0}"
    local after="${3:-1}"
    if [ -f "$file" ]; then
        grep -i -E -B "$before" -A "$after" -- "$QUERY_REGEX" "$file" 2>/dev/null | head -15 \
            || echo "  no match"
    else
        echo "  (file not found)"
    fi
}

# 1. PATTERNS.md — explicit reusable templates (highest reuse signal) ---------
print_header "patterns (reusable templates — start here for RAG)"
ctx_grep "$HOME/claude-hq/docs/PATTERNS.md" 1 3

# 2. ANTI-PATTERNS.md — what NOT to suggest -----------------------------------
print_header "anti-patterns (do NOT suggest these)"
ctx_grep "$HOME/claude-hq/docs/ANTI-PATTERNS.md" 1 3

# 3. Vault Decision Log -------------------------------------------------------
print_header "decision log (provenance-tagged decisions)"
DECISION_LOG="$HOME/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/claude-hq/Decision Log.md"
ctx_grep "$DECISION_LOG" 1 3

# 4. BACKLOG.md ---------------------------------------------------------------
print_header "backlog (parked work)"
ctx_grep "$HOME/claude-hq/docs/BACKLOG.md" 0 2

# 5. LESSONS.md ---------------------------------------------------------------
print_header "lessons (preventive rules)"
ctx_grep "$HOME/claude-hq/commander/LESSONS.md" 0 3

# 6. Commander doctrines (COMMUNICATION, MODEL_ROUTING, COST_CONTROL, etc.) ---
print_header "commander doctrines"
for doctrine in COMMUNICATION MODEL_ROUTING COST_CONTROL TRUST_GATE INCIDENT_LEDGER BORIS_PRINCIPLES; do
    f="$HOME/claude-hq/commander/${doctrine}.md"
    if [ -f "$f" ] && grep -i -q -E -- "$QUERY_REGEX" "$f" 2>/dev/null; then
        echo "  [$doctrine]"
        grep -i -E -B 0 -A 1 -- "$QUERY_REGEX" "$f" 2>/dev/null | head -6 | sed 's/^/    /'
    fi
done

# 7. Scripts INDEX — "we have a script for that" -----------------------------
print_header "scripts index"
ctx_grep_short "$HOME/claude-hq/scripts/INDEX.md" 0 0

# 8. Tool / agent registries --------------------------------------------------
print_header "tool registry (registry.json)"
if [ -f "$HOME/claude-hq/registry.json" ]; then
    python3 - "$QUERY_REGEX" <<'PY' 2>&1 | head -15
import json, re, sys
from pathlib import Path
rx = re.compile(sys.argv[1], re.IGNORECASE)
data = json.loads(Path.home().joinpath('claude-hq/registry.json').read_text())
hits = []
for tool in data.get('tools', []):
    blob = ' '.join(filter(None, [
        tool.get('id',''), tool.get('name',''), tool.get('description',''),
        ' '.join(tool.get('activation_triggers', []) or []),
    ]))
    if rx.search(blob):
        hits.append(f"  {tool.get('id'):<35} — {tool.get('description','')[:80]}")
if hits:
    for h in hits[:5]: print(h)
else:
    print("  no match")
PY
else
    echo "  registry.json not found"
fi

print_header "agent bank (agents/registry.json)"
if [ -f "$HOME/claude-hq/agents/registry.json" ]; then
    python3 - "$QUERY_REGEX" <<'PY' 2>&1 | head -10
import json, re, sys
from pathlib import Path
rx = re.compile(sys.argv[1], re.IGNORECASE)
data = json.loads(Path.home().joinpath('claude-hq/agents/registry.json').read_text())
agents = data.get('agents', []) if isinstance(data, dict) else []
hits = []
for ag in agents:
    blob = ' '.join(filter(None, [
        ag.get('id',''), ag.get('name',''), ag.get('description',''),
        ' '.join(ag.get('activation_triggers', []) or []),
    ]))
    if rx.search(blob):
        hits.append(f"  {ag.get('id'):<30} — {ag.get('description','')[:80]}")
if hits:
    for h in hits[:5]: print(h)
else:
    print("  no match")
PY
else
    echo "  agent registry not found"
fi

# 9. Mission Boards — how past projects were decomposed -----------------------
print_header "mission boards (project decompositions)"
MISSION_HITS=0
for mb in \
    "$HOME/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/PATS-Copy/03 Mission Board.md" \
    "$HOME/Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/ai-agent-fleet-ventures/03 Mission Board.md" \
    "$HOME/projects/ai-agent-fleet-ventures/MISSION_BOARD.md" \
    "$HOME/projects/kl-talent-search/MISSION_BOARD.md" \
    "$HOME/projects/moodboard-generator/MISSION_BOARD.md" \
; do
    if [ -f "$mb" ] && grep -i -q -E -- "$QUERY_REGEX" "$mb" 2>/dev/null; then
        proj=$(basename "$(dirname "$mb")")
        echo "  [$proj]"
        grep -i -E -B 0 -A 2 -- "$QUERY_REGEX" "$mb" 2>/dev/null | head -8 | sed 's/^/    /'
        MISSION_HITS=$((MISSION_HITS+1))
    fi
done
[ "$MISSION_HITS" = "0" ] && echo "  no match"

# 10. MemPalace ---------------------------------------------------------------
print_header "mempalace (semantic search across mined drawers)"
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
echo "(probe complete · trust hierarchy: patterns > anti-patterns > decision log > backlog > lessons > commander doctrines > registries > mission boards > mempalace > hindsight)"
