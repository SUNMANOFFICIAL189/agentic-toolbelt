# MemPalace Corruption — Recovery Runbook

> **Purpose:** When `mempalace mine` or `mempalace search` segfaults
> (exit code 139), follow this runbook. Drafted 2026-05-08 after the
> chroma segment_id drift incident, which took ~90 minutes to debug
> from cold. Following these steps it should take ~10 minutes.

---

## Quick triage

```bash
# 1. Reproduce
mempalace mine ~/claude-hq; echo "exit=$?"
# exit=139 → segfault, this runbook applies
# exit=0   → not a corruption issue, look elsewhere

# 2. Confirm with the precheck script
python3 ~/claude-hq/scripts/mempalace-precheck.py
# exit=0 → healthy, segfault has another cause
# exit=2 → corruption confirmed, proceed below
```

---

## Symptoms

The recurring corruption shape (seen 2026-05-08):

1. `mempalace mine <project>` exits with code 139 (SIGSEGV)
2. `mempalace search <query>` exits with code 139
3. `mempalace status` works fine — only operations that touch the HNSW
   vector index crash
4. macOS crash report at `~/Library/Logs/DiagnosticReports/Python-*.ips`
   shows fault in `hnswlib::HierarchicalNSW<float>::searchBaseLayer` or
   `addPoint`

If you see **all of those**, this is the same incident class.

---

## Root cause (what's actually broken)

ChromaDB's local store has three places that need to agree on segment IDs:

| Place | What it stores |
|---|---|
| `palace/chroma.sqlite3` → `segments` table | The currently-active vector + metadata segment IDs |
| `palace/chroma.sqlite3` → `embeddings` table | Each embedding's `segment_id` (must match an active segment) |
| `palace/<UUID>/` directories | The on-disk HNSW index files, one dir per active vector segment |

When chroma upgrades, or when a `mempalace mine` gets killed mid-write, these can drift apart. Two specific failure modes:

- **Orphan embeddings:** `embeddings.segment_id` references a UUID that's no longer in the `segments` table. Chroma's collection driver thinks it has 0 records even though sqlite has thousands.
- **Orphan on-disk dir:** A `<UUID>/` directory exists for a segment that's no longer in the segments table. ChromaDB tries to load the index from it and segfaults.

Both shapes were present in the 2026-05-08 incident.

---

## Fix path

Two paths depending on how much time you want to spend:

### Path A — Surgical recovery (preserves data, ~5 minutes, sometimes works)

Try this first. If chroma's count() returns the expected number after the SQL update, you're done.

```bash
# 1. Backup
cp -R ~/.mempalace/palace ~/.mempalace/palace.backup-$(date +%Y%m%d-%H%M%S)

# 2. Find orphan UUID dirs and move them aside
python3 -c "
import os, sqlite3
PALACE = os.path.expanduser('~/.mempalace/palace')
db = sqlite3.connect(f'{PALACE}/chroma.sqlite3')
in_db = {r[0] for r in db.execute('SELECT id FROM segments')}
on_disk = {d for d in os.listdir(PALACE) if os.path.isdir(f'{PALACE}/{d}') and not d.startswith('.')}
print('orphans on disk:', on_disk - in_db)
"
# For each printed orphan, move aside:
mv ~/.mempalace/palace/<ORPHAN-UUID> ~/.mempalace/palace.orphaned-<UUID>-$(date +%H%M%S)

# 3. Find which segment_id embeddings reference vs the active vector segment
python3 -c "
import sqlite3, os
db = sqlite3.connect(os.path.expanduser('~/.mempalace/palace/chroma.sqlite3'))
print('Active vector segment:')
for r in db.execute(\"SELECT id FROM segments WHERE type LIKE '%hnsw%'\"): print(' ', r[0])
print('Distinct segment_ids in embeddings:')
for r in db.execute('SELECT segment_id, COUNT(*) FROM embeddings GROUP BY segment_id'): print(' ', r)
"

# 4. Retarget embeddings to the active segment (ONLY if there's exactly one
#    active vector segment and one orphan segment_id — otherwise stop)
python3 -c "
import sqlite3, os
db = sqlite3.connect(os.path.expanduser('~/.mempalace/palace/chroma.sqlite3'))
db.execute('UPDATE embeddings SET segment_id = ? WHERE segment_id = ?',
           ('<ACTIVE-VECTOR-UUID>', '<OLD-ORPHAN-UUID>'))
db.execute('DELETE FROM max_seq_id WHERE segment_id NOT IN (SELECT id FROM segments)')
db.commit()
"

# 5. Verify chroma now sees the data
python3 -c "
import chromadb
c = chromadb.PersistentClient(path=os.path.expanduser('~/.mempalace/palace'))
col = c.get_collection('mempalace_drawers')
print('count after fix:', col.count())
"
```

If `count()` returns the expected number (i.e., comparable to `SELECT COUNT(*) FROM embeddings`), surgery succeeded. Test `mempalace search "<query>"` to confirm. If `count()` still returns 0, surgery failed — chroma's in-memory segment driver isn't picking up the existing rows. Move to Path B.

### Path B — Clean reset + re-mine (always works, ~10-15 minutes, loses derived data)

This is what worked on 2026-05-08. The drawers in MemPalace are derived from project source files, so re-mining rebuilds them.

```bash
# 1. Backup current palace (you already have one from Path A — skip if so)
mv ~/.mempalace/palace ~/.mempalace/palace.backup-$(date +%Y%m%d-%H%M%S)

# 2. Re-mine each project that had a wing
mempalace mine ~/projects/corporate-brains
mempalace mine ~/Desktop/POLYMARKET_TRADING_3.0
mempalace mine ~/projects/paperclip
mempalace mine ~/claude-hq

# 3. Verify
mempalace status
mempalace search "trust gate"
```

Wing list to mine is determined by which project directories have a `mempalace.yaml` file. Find them with:
```bash
find ~/projects ~/Desktop ~/claude-hq -maxdepth 3 -name "mempalace.yaml" 2>/dev/null
```

---

## Prevention — what's in place since 2026-05-08

Three guardrails added after the incident:

1. **Pre-mine integrity check** (`~/claude-hq/scripts/mempalace-precheck.py`)
   - Runs read-only sqlite checks before every mine
   - Catches orphan embeddings, orphan on-disk dirs, stuck embeddings_queue
   - Exit 2 → mine aborts; corruption logged before it spreads

2. **Lockfile in session-end hook** (`~/.claude/hooks/session-end.sh`)
   - Atomic noclobber-lock at `~/.mempalace/.mine.lock`
   - Only one mine ever runs at a time across all sessions
   - Concurrent attempts skip silently rather than racing

3. **`nohup` survival** (`~/.claude/hooks/session-end.sh`)
   - Mine ignores SIGHUP when Terminal closes
   - `disown` removes it from the shell's job table
   - Mid-write SIGKILL no longer corrupts state

Mine output is logged to `~/.mempalace/mine.log` so background runs can be inspected.

---

## When to revisit

Mark this runbook obsolete if:

- ChromaDB ships an internal version-migration tool that handles segment-ID drift
  cleanly (would replace Path A's surgery)
- mempalace gains its own `repair` command that actually works (the existing
  `repair` subcommand also segfaults on this corruption shape — verified 2026-05-08)
- We migrate off chroma to a vector store with stronger consistency (qdrant,
  pgvector with native SQL FK constraints)

Until then, this runbook is the canonical recovery path.

---

## See also

- Decision Log entry — `Vaults/Jarvis-Brain/JARVIS-BRAIN/Projects/claude-hq/Decision Log.md` (2026-05-08 entry "MemPalace corruption fixed")
- Precheck source — `~/claude-hq/scripts/mempalace-precheck.py`
- Hook source — `~/.claude/hooks/session-end.sh` Layer 5
- Original incident commit — captured in HQ git log under `chore(mempalace): ...`
