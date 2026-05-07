#!/usr/bin/env python3
"""
Backfill historical Supabase rows where the bot's pnl-write was lost.

Pulls all `status='stopped' AND pnl=0 AND our_size>0` rows. For each, tries to
find the real pnl from PM2 logs on the server by matching the 8-char trade-id
prefix in `Paper copy trade CLOSED` log lines. Outputs proposed updates as
JSON for review. By default does NOT apply — pass --apply to commit changes.

Usage:
    python backfill_pnl_writes.py            # dry run, prints proposed updates
    python backfill_pnl_writes.py --apply    # apply via Supabase REST PATCH

Calibrated against 2026-05-07 Phase A finding: 11 of 30 recent SELL stops in
the last 7 days had pnl=0 in db. Bot's in-memory state had real pnls; the
audit gap was -$925. This script closes that gap for rows where logs exist.

Reference:
    ~/claude-hq/docs/BACKLOG.md → "PATS-Copy: Supabase pnl-write reliability"
    Bug fix: fix/pnl-write-reliability branch (commit on 2026-05-08)
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# Repo-relative lib import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.creds import supabase_creds  # type: ignore[import-not-found]

SSH_HOST = "root@204.168.204.247"
LOG_DIR = "/opt/polymarket-bot/logs/"

# Match: ... Paper copy trade CLOSED (reason) {"id":"PREFIX",...,"pnl":"$-943.04",...}
LOG_LINE_RE = re.compile(
    r'Paper copy trade CLOSED \([^)]+\) \{"id":"(?P<idprefix>[a-f0-9]{8})".*?"pnl":"\$(?P<pnl>-?[\d.]+)"'
)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore[import-not-found]
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_suspect_rows() -> list[dict]:
    """All status=stopped + pnl=0 + our_size>0 rows."""
    url, key = supabase_creds()
    params = {
        "select": "id,market_id,leader_wallet,side,our_size,our_entry_price,pnl,entry_time,exit_time",
        "status": "eq.stopped",
        "pnl": "eq.0",
        "our_size": "gt.0",
        "order": "exit_time.desc",
        "limit": "200",
    }
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}/rest/v1/copy_trades?{qs}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_log_pnls() -> dict[str, float]:
    """Pull all `Paper copy trade CLOSED` lines from server logs.

    Returns dict mapping 8-char id prefix → most recent logged pnl for that prefix.
    If a prefix appears multiple times (different UUIDs sharing first 8 chars), the
    LAST value wins — caller must verify uniqueness before applying.
    """
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", SSH_HOST,
         f"grep -rh 'Paper copy trade CLOSED' {LOG_DIR} 2>/dev/null"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    pnls: dict[str, float] = {}
    duplicates: dict[str, list[float]] = {}
    for line in out.stdout.splitlines():
        m = LOG_LINE_RE.search(line)
        if not m:
            continue
        idprefix = m.group("idprefix")
        pnl = float(m.group("pnl"))
        if idprefix in pnls and pnls[idprefix] != pnl:
            duplicates.setdefault(idprefix, [pnls[idprefix]]).append(pnl)
        pnls[idprefix] = pnl
    if duplicates:
        print(f"# WARN: {len(duplicates)} id-prefix collision(s) — caller must verify",
              file=sys.stderr)
        for k, vs in duplicates.items():
            print(f"#   {k}: {vs}", file=sys.stderr)
    return pnls


def apply_update(row_id: str, new_pnl: float) -> bool:
    """PATCH a single row's pnl. Returns True on success."""
    url, key = supabase_creds()
    body = json.dumps({"pnl": new_pnl}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/rest/v1/copy_trades?id=eq.{row_id}",
        data=body,
        method="PATCH",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:  # type: ignore[name-defined]
        print(f"#   PATCH failed for {row_id}: HTTP {e.code} {e.reason}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Backfill lost pnl writes from logs.")
    p.add_argument("--apply", action="store_true",
                   help="Actually PATCH Supabase. Default is dry-run.")
    args = p.parse_args(argv)

    rows = fetch_suspect_rows()
    print(f"# {len(rows)} suspect row(s) (status=stopped, pnl=0, our_size>0)")
    if not rows:
        return 0

    log_pnls = fetch_log_pnls()
    print(f"# {len(log_pnls)} unique id-prefixes found in server logs")
    print()

    proposed: list[tuple[dict, float]] = []
    unrecoverable: list[dict] = []

    for r in rows:
        prefix = r["id"][:8]
        if prefix in log_pnls:
            proposed.append((r, log_pnls[prefix]))
        else:
            unrecoverable.append(r)

    print(f"## RECOVERABLE — {len(proposed)} row(s) with matching log evidence")
    total_recovered = 0.0
    for r, new_pnl in proposed:
        total_recovered += new_pnl
        print(f"  {r['id'][:8]}  {r['side']:4} {r['market_id'][:50]:50}  "
              f"size=${r['our_size']:>5.1f} entry={r['our_entry_price']:.4f} "
              f"  pnl: 0.00 → {new_pnl:+8.2f}  exit {r['exit_time'][:19]}")
    print(f"\n  total recovered pnl: ${total_recovered:+.2f}")

    print(f"\n## UNRECOVERABLE — {len(unrecoverable)} row(s) with no log match")
    for r in unrecoverable:
        print(f"  {r['id'][:8]}  {r['side']:4} {r['market_id'][:50]:50}  "
              f"size=${r['our_size']:>5.1f} entry={r['our_entry_price']:.4f} "
              f"  exit {r['exit_time'][:19]}")
    print("\n  (these were likely closed by reconciliation only, never went through")
    print("   paperEngine.closeTrade — no log line was ever emitted with the real pnl)")

    if not args.apply:
        print("\n# DRY RUN — pass --apply to PATCH Supabase")
        return 0

    print(f"\n# APPLYING {len(proposed)} updates to Supabase...")
    ok = 0
    fail = 0
    for r, new_pnl in proposed:
        if apply_update(r["id"], new_pnl):
            ok += 1
        else:
            fail += 1
    print(f"# done: {ok} succeeded, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
