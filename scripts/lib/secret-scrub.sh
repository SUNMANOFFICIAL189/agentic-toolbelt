#!/usr/bin/env bash
# Session-end secret scrubber — redact any secret-shaped strings that leaked
# into local persistence stores (session transcripts, claude-mem DB, MemPalace
# chroma, Obsidian vault) before the vault gets pushed to GitHub.
#
# Scope: LOCAL DISK ONLY. This cannot retract content from the Anthropic API
# backend, your shell history, or any third-party log sinks. For full safety,
# rotate exposed keys at source.
#
# Patterns: well-known secret shapes (Anthropic/OpenAI/GitHub/Google/AWS/Slack
# + SSH private keys). Matches are replaced with [REDACTED:<pattern-type>].
#
# Usage (standalone):
#   bash ~/claude-hq/scripts/lib/secret-scrub.sh scrub_all
#
# Usage (from session-end.sh):
#   source ~/claude-hq/scripts/lib/secret-scrub.sh
#   scrub_all

set -euo pipefail

SCRUB_LOG="${SCRUB_LOG:-$HOME/claude-hq/scripts/.secret-scrub.log}"
CLAUDE_MEM_DB="${CLAUDE_MEM_DB:-$HOME/.claude-mem/claude-mem.db}"
MEMPALACE_DB="${MEMPALACE_DB:-$HOME/.mempalace/palace/chroma.sqlite3}"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Vaults/Jarvis-Brain}"
CC_SESSIONS_ROOT="${CC_SESSIONS_ROOT:-$HOME/Library/Application Support/Claude/claude-code-sessions}"

# Known secret patterns (ERE). Keep names and regexes in sync with
# scripts/lib/secret-scan.sh:SECRET_PATTERNS.
SCRUB_PATTERNS=(
  'anthropic:sk-ant-[A-Za-z0-9_-]{20,}'
  'openai:sk-[A-Za-z0-9]{32,}'
  'github-pat:ghp_[A-Za-z0-9]{30,}'
  'github-oauth:gho_[A-Za-z0-9]{30,}'
  'google-api:AIza[A-Za-z0-9_-]{35}'
  'aws-access:AKIA[0-9A-Z]{16}'
  'slack:xox[baprs]-[0-9a-zA-Z-]{10,}'
  'reddit-secret:[A-Za-z0-9_-]{27,30}(?=[^A-Za-z0-9_-]|$)'   # heuristic; matches client-secret shape
)

_log() {
  mkdir -p "$(dirname "$SCRUB_LOG")"
  echo "[$(date '+%F %T')] $*" >> "$SCRUB_LOG"
}

# Build Python regex-union string (used by Python redactor).
_py_pattern_union() {
  python3 - <<'PY'
patterns = [
    ("anthropic",    r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("openai",       r"sk-[A-Za-z0-9]{32,}"),
    ("github_pat",   r"ghp_[A-Za-z0-9]{30,}"),
    ("github_oauth", r"gho_[A-Za-z0-9]{30,}"),
    ("google_api",   r"AIza[A-Za-z0-9_-]{35}"),
    ("aws_access",   r"AKIA[0-9A-Z]{16}"),
    ("slack",        r"xox[baprs]-[0-9a-zA-Z-]{10,}"),
]
import json
print(json.dumps(patterns))
PY
}

# ------------------------------------------------------------------
# 1. Session transcripts (Claude Code JSON transcripts)
# ------------------------------------------------------------------
scrub_transcripts() {
  local root="$CC_SESSIONS_ROOT"
  [[ -d "$root" ]] || { _log "transcripts: dir missing $root"; return 0; }

  local touched
  touched=$(python3 - "$root" <<'PY'
import json, os, re, sys
root = sys.argv[1]

patterns = [
    # Lowered min-lengths so partial prefixes (e.g. someone pasting the first
    # 15-20 chars in a grep) are also caught. False-positive risk is low
    # because the prefix alone is distinctive.
    ("anthropic",    re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}")),
    ("openai",       re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("github_pat",   re.compile(r"ghp_[A-Za-z0-9]{15,}")),
    ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{15,}")),
    ("google_api",   re.compile(r"AIza[A-Za-z0-9_-]{15,}")),
    ("aws_access",   re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack",        re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}")),
    # Reddit OAuth client secrets are 27-30 chars of [A-Za-z0-9_-] with no
    # distinguishing prefix — we pin-match only the specific compromised one.
    ("reddit_sec",   re.compile(r"I3WI6Wmz_u-lAUjBuA[A-Za-z0-9_-]*")),
]

touched = 0
for dirpath, _, filenames in os.walk(root):
    for fn in filenames:
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(dirpath, fn)
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                body = f.read()
        except OSError:
            continue
        new = body
        for name, rx in patterns:
            new = rx.sub(f"[REDACTED:{name}]", new)
        if new != body:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(new)
            touched += 1
            print(fp)
print(f"__COUNT__ {touched}", file=sys.stderr)
PY
)
  _log "transcripts: scrubbed -> $touched"
}

# ------------------------------------------------------------------
# 2. claude-mem sqlite DB (observations, user_prompts, session_summaries)
# ------------------------------------------------------------------
scrub_claude_mem() {
  local db="$CLAUDE_MEM_DB"
  [[ -f "$db" ]] || { _log "claude-mem: db missing $db"; return 0; }

  python3 - "$db" <<'PY'
import sqlite3, re, sys
db = sys.argv[1]

patterns = [
    ("anthropic",    re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}")),
    ("openai",       re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("github_pat",   re.compile(r"ghp_[A-Za-z0-9]{15,}")),
    ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{15,}")),
    ("google_api",   re.compile(r"AIza[A-Za-z0-9_-]{15,}")),
    ("aws_access",   re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack",        re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}")),
    ("reddit_sec",   re.compile(r"I3WI6Wmz_u-lAUjBuA[A-Za-z0-9_-]*")),
]

targets = [
    ("observations",      ["text", "facts", "narrative", "title", "subtitle", "concepts"]),
    ("user_prompts",      ["prompt_text"]),
    ("session_summaries", ["request", "investigated", "learned", "completed", "next_steps"]),
]

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
total = 0

for table, cols in targets:
    try:
        cur.execute(f"SELECT id, {', '.join(cols)} FROM {table}")
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"[skip] {table}: {e}", file=sys.stderr)
        continue
    for row in rows:
        updates = {}
        for c in cols:
            v = row[c]
            if v is None:
                continue
            new = v
            for name, rx in patterns:
                new = rx.sub(f"[REDACTED:{name}]", new)
            if new != v:
                updates[c] = new
        if updates:
            setclause = ", ".join(f"{c} = ?" for c in updates)
            params = list(updates.values()) + [row["id"]]
            cur.execute(f"UPDATE {table} SET {setclause} WHERE id = ?", params)
            total += 1

conn.commit()

# Rebuild FTS indexes to match redacted content
for fts_table in ("observations_fts", "user_prompts_fts", "session_summaries_fts"):
    try:
        cur.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
    except sqlite3.OperationalError:
        pass

conn.commit()
conn.close()
print(f"claude-mem: {total} rows redacted", file=sys.stderr)
PY
  _log "claude-mem: scrub pass complete"
}

# ------------------------------------------------------------------
# 3. MemPalace chroma fulltext (DETECT only — deletion would corrupt
# the vector DB. Logs matches for manual review.)
# ------------------------------------------------------------------
scrub_mempalace() {
  local db="$MEMPALACE_DB"
  [[ -f "$db" ]] || { _log "mempalace: db missing $db"; return 0; }

  python3 - "$db" "$SCRUB_LOG" <<'PY'
import sqlite3, re, sys
db, log = sys.argv[1], sys.argv[2]

patterns = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{15,}"),
    re.compile(r"gho_[A-Za-z0-9]{15,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{15,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[0-9a-zA-Z-]{10,}"),
    re.compile(r"I3WI6Wmz_u-lAUjBuA[A-Za-z0-9_-]*"),
]

conn = sqlite3.connect(db)
cur = conn.cursor()
try:
    cur.execute("SELECT rowid, string_value FROM embedding_fulltext_search")
    rows = cur.fetchall()
except sqlite3.OperationalError as e:
    print(f"[skip] mempalace fts: {e}", file=sys.stderr)
    sys.exit(0)

hits = []
for rid, val in rows:
    if val is None:
        continue
    for rx in patterns:
        if rx.search(val):
            hits.append((rid, val[:80]))
            break

if hits:
    with open(log, "a") as f:
        f.write(f"\n[mempalace] DETECTED {len(hits)} row(s) with secret-shaped content — manual review needed:\n")
        for rid, preview in hits[:20]:
            f.write(f"  rowid={rid}  preview={preview!r}\n")
    print(f"mempalace: {len(hits)} suspicious rows — logged for manual review", file=sys.stderr)
else:
    print("mempalace: clean", file=sys.stderr)

conn.close()
PY
  _log "mempalace: scrub pass complete"
}

# ------------------------------------------------------------------
# 4. Obsidian vault — refuse to let session-end push if anything matches
# ------------------------------------------------------------------
scrub_vault() {
  local root="$VAULT_ROOT"
  [[ -d "$root" ]] || { _log "vault: dir missing $root"; return 0; }

  # Exclude .git and common binary/cache dirs
  local found
  found=$(find "$root" -type f \
    \( -name "*.md" -o -name "*.txt" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.canvas" \) \
    -not -path "*/.git/*" \
    -not -path "*/.obsidian/workspace*" \
    -exec grep -lE 'sk-ant-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{15,}|AIza[A-Za-z0-9_-]{15,}|AKIA[0-9A-Z]{16}|xox[baprs]-[0-9a-zA-Z-]{10,}|I3WI6Wmz_u-lAUjBuA' {} \; 2>/dev/null || true)

  if [[ -n "$found" ]]; then
    _log "vault: HALT — secret-shaped strings detected in:"
    echo "$found" | while read -r f; do _log "  $f"; done
    # Touch a sentinel so session-end.sh can refuse to push
    touch "$root/.scrub-halt"
    return 1
  fi

  # Remove any previous halt sentinel if we're clean now
  rm -f "$root/.scrub-halt"
  _log "vault: clean"
  return 0
}

# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------
scrub_all() {
  _log "=== scrub_all start ==="
  scrub_transcripts || true
  scrub_claude_mem  || true
  scrub_mempalace   || true
  scrub_vault       || true
  _log "=== scrub_all end ==="
}

# Run directly if invoked as a script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  scrub_all
fi
