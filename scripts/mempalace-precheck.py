#!/usr/bin/env python3
"""
mempalace-precheck — fast, read-only consistency check on the MemPalace
chroma store. Designed to run before `mempalace mine` so we abort if the
store is corrupt rather than mining into a broken state and spreading damage.

Built 2026-05-08 after the chroma segment_id drift incident. See
~/claude-hq/docs/mempalace-corruption-runbook.md for the full incident write-up.

Exit codes (consumed by hook scripts):
  0   palace is healthy or doesn't exist yet (mine OK to proceed)
  2   corruption detected — mine should ABORT and a Telegram alert should fire
  3   palace store unreachable (sqlite open failed, etc.) — non-fatal, log only

Read-only — never mutates the palace.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

PALACE_DIR = Path(os.path.expanduser("~/.mempalace/palace"))
SQLITE_PATH = PALACE_DIR / "chroma.sqlite3"


def _emit_warn(msg: str) -> None:
    print(f"[mempalace-precheck] WARN: {msg}", file=sys.stderr)


def _emit_info(msg: str) -> None:
    print(f"[mempalace-precheck] {msg}", file=sys.stderr)


def main() -> int:
    if not SQLITE_PATH.exists():
        # Fresh install or freshly-deleted-for-rebuild — that's fine
        _emit_info("no palace yet at " + str(SQLITE_PATH) + " — skipping check")
        return 0

    try:
        db = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)
        db.execute("PRAGMA query_only=1")
    except sqlite3.Error as e:
        _emit_warn(f"sqlite open failed: {e}")
        return 3

    issues: list[str] = []

    # CHECK 1 — every embedding's segment_id must exist in segments table.
    # This is the exact corruption shape from 2026-05-08: embeddings pointed
    # at a segment that no longer existed.
    try:
        cur = db.execute(
            "SELECT segment_id, COUNT(*) FROM embeddings "
            "WHERE segment_id NOT IN (SELECT id FROM segments) "
            "GROUP BY segment_id"
        )
        orphans = cur.fetchall()
        if orphans:
            for seg_id, count in orphans:
                issues.append(
                    f"{count} embedding(s) reference segment '{seg_id}' which is not in the segments table"
                )
    except sqlite3.Error as e:
        _emit_warn(f"orphan-embedding check failed: {e}")
        return 3

    # CHECK 2 — every on-disk UUID directory should match an active segment.
    # Orphaned UUID dirs (like 836a42ae- on 2026-05-08) cause segfaults at mine time.
    try:
        on_disk = {
            d.name
            for d in PALACE_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            # Heuristic: UUIDs are 36 chars with dashes
            and len(d.name) == 36 and d.name.count("-") == 4
        }
        in_db = {row[0] for row in db.execute("SELECT id FROM segments")}
        orphan_dirs = on_disk - in_db
        if orphan_dirs:
            issues.append(
                "on-disk UUID dir(s) without matching segment: "
                + ", ".join(sorted(orphan_dirs))
            )
    except OSError as e:
        _emit_warn(f"on-disk dir scan failed: {e}")
        # Not fatal — segment-level orphans are the more dangerous shape

    # CHECK 3 — embeddings_queue should be empty or small.
    # A massive queue (>10000) suggests a mine that didn't drain properly.
    try:
        n_queue = next(db.execute("SELECT COUNT(*) FROM embeddings_queue"))[0]
        if n_queue > 10000:
            issues.append(
                f"embeddings_queue has {n_queue} pending items — previous mine may not have completed cleanly"
            )
    except sqlite3.Error:
        # Older chroma may not have this table — skip
        pass

    db.close()

    if not issues:
        _emit_info("palace OK")
        return 0

    print("\n[mempalace-precheck] CORRUPTION DETECTED — mine aborted to prevent spread:", file=sys.stderr)
    for i, msg in enumerate(issues, 1):
        print(f"  {i}. {msg}", file=sys.stderr)
    print(
        "\n  Recovery runbook: ~/claude-hq/docs/mempalace-corruption-runbook.md\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
