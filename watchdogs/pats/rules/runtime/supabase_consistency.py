#!/usr/bin/env python3
"""
Runtime rule: Supabase ↔ bot in-memory state consistency.

Catches stale "open" rows that the bot has stopped tracking. Two failure
modes covered:

  1. Row marked 'open' in Supabase but the bot's .bot-status.json reports
     a smaller open-position count → the row is stale; close write failed
     or the row was orphaned.

  2. Row marked 'open' in Supabase with no entry update in N hours when
     the bot is alive — likely a duplicate write from a re-entry race.

Designed to detect the kind of orphaned rows that 2026-05-07 session
manually cleaned up via the `ac4f382a-9afd-49d5-8879-a0364ac4bda8` Supabase
edit. The watchdog should surface these instead of requiring manual finds.

Usage:
    python rules/runtime/supabase_consistency.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.supabase import query

RULE_ID = "pats-runtime-supabase-consistency"
STALE_HOURS = 72  # entry older than this AND still 'open' is suspect


def main() -> int:
    db_open_rows = query(
        "copy_trades",
        select="id,market_id,leader_wallet,side,status,entry_time",
        filters={"status": "in.(open,pending)"},
        order="entry_time.desc",
        limit=200,
    )
    db_open_count = len(db_open_rows)

    bot_status = _fetch_bot_status()
    bot_open_count = bot_status.get("openPositions", -1) if bot_status else -1

    # Failure mode 1: db count doesn't match bot count (and we got a bot reading)
    if bot_open_count >= 0 and db_open_count != bot_open_count:
        finding = Finding(
            rule_id=f"{RULE_ID}.count-mismatch",
            severity="warn",
            what_happened=(
                f"The database thinks the bot has {db_open_count} open position(s) "
                f"but the bot itself reports {bot_open_count}. "
                f"There are {abs(db_open_count - bot_open_count)} stale row(s) somewhere."
            ),
            what_to_do=(
                "Run the proactive health check from CLAUDE.md, then compare the "
                "open-positions list in Supabase against the bot's open trades. "
                "Mark any orphan row as 'stopped' with a manual exit time."
            ),
            technical_detail={
                "rule_id": f"{RULE_ID}.count-mismatch",
                "db_open_count": db_open_count,
                "bot_open_count": bot_open_count,
                "db_open_rows": db_open_rows[:20],
            },
        )
        emit(finding)

    # Failure mode 2: any open row with entry older than STALE_HOURS
    threshold = datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)
    stale = []
    for r in db_open_rows:
        try:
            et = _parse_iso(r["entry_time"])
            if et < threshold:
                stale.append({
                    "id": r["id"],
                    "market_id": r["market_id"],
                    "entry_time": r["entry_time"],
                    "age_hours": round((datetime.now(timezone.utc) - et).total_seconds() / 3600, 1),
                })
        except (ValueError, KeyError):
            continue

    if stale:
        sample = stale[0]
        finding = Finding(
            rule_id=f"{RULE_ID}.stale-open-row",
            severity="warn",
            what_happened=(
                f"There are {len(stale)} 'open' row(s) in the database that have been "
                f"sitting for more than {STALE_HOURS} hours. The oldest is "
                f"\"{sample['market_id'][:50]}\" — open for {sample['age_hours']:.0f} hours."
            ),
            what_to_do=(
                "Check whether the bot still has these positions open in memory. "
                "If yes, the position is genuinely stuck — investigate the lifecycle "
                "manager. If no, mark the row as 'stopped' in Supabase to clear the orphan."
            ),
            technical_detail={
                "rule_id": f"{RULE_ID}.stale-open-row",
                "stale_hours_threshold": STALE_HOURS,
                "stale_count": len(stale),
                "stale_rows": stale,
            },
        )
        emit(finding)

    return 0


def _fetch_bot_status() -> dict | None:
    try:
        out = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "root@204.168.204.247",
             "cat /opt/polymarket-bot/.bot-status.json"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return json.loads(out.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        print(f"# transient: supabase unreachable: {e}", file=sys.stderr)
        sys.exit(0)
