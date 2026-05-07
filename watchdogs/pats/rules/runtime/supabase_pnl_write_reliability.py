#!/usr/bin/env python3
"""
Runtime rule: Supabase pnl-write reliability.

Catches the impossible state of `status='stopped' AND pnl=0 AND our_size>0`.
A stop-loss closure should always have a non-zero pnl (positive for SELL
profits, negative for losses). pnl=0 on a stopped row means the bot's
update path lost the value — the bot's in-memory accounting has the real
loss but Supabase doesn't, so audit reconstruction (e.g., the 2026-05-07
Phase A balance investigation) underreports.

Calibrated against 2026-05-07 finding: 11 of 30 recent low-priced SELL
stops had pnl=0 in db while bot logged real losses (incl. the -$943 BTC
trade). All-time db sum(pnl) = +$158 vs bot reports -$767 = $925 audit gap.

Phase A → BACKLOG → this rule.

Usage:
    python rules/runtime/supabase_pnl_write_reliability.py
    # emits one Finding JSON line per impossible row, exits 0
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent dir to import lib.* (works regardless of cwd)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.supabase import query

RULE_ID = "pats-runtime-supabase-pnl-write-reliability"
LOOKBACK_HOURS = 24  # only flag recent rows; older ones are historical and acked


def main() -> int:
    # status=stopped + pnl exactly 0 + our_size > 0 is the impossible state
    rows = query(
        "copy_trades",
        select="id,market_id,leader_wallet,side,our_size,our_entry_price,pnl,exit_time,entry_time",
        filters={
            "status": "eq.stopped",
            "pnl": "eq.0",
            "our_size": "gt.0",
            "exit_time": f"gte.{_iso_lookback(LOOKBACK_HOURS)}",
        },
        order="exit_time.desc",
        limit=50,
    )

    if not rows:
        return 0

    # Plain-English alert summarises the pattern; technical rows go to audit.log only
    sample_market = rows[0]["market_id"]
    count = len(rows)
    finding = Finding(
        rule_id=RULE_ID,
        severity="warn",
        what_happened=(
            f"The bot recorded {count} stop-loss close(s) in the last day where "
            f"the database shows zero loss but the bot's own books reflect a real loss. "
            f"The numbers in Supabase are wrong; the bot itself is correct. "
            f"First example: \"{sample_market[:60]}\"."
        ),
        what_to_do=(
            "Run the BACKLOG item 'PATS-Copy: Supabase pnl-write reliability' to "
            "find which close path skips the pnl write and backfill the missing rows."
        ),
        technical_detail={
            "lookback_hours": LOOKBACK_HOURS,
            "count": count,
            "rule_id": RULE_ID,
            "rows": rows,
        },
    )
    emit(finding)
    return 0


def _iso_lookback(hours: int) -> str:
    from datetime import datetime, timedelta, timezone
    t = datetime.now(timezone.utc) - timedelta(hours=hours)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    sys.exit(main())
