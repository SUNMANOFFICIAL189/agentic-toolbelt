#!/usr/bin/env python3
"""
One-shot reminder: count PATS sessions in the watchdog DB and email Sunil
a plain-English status update.

Scheduled by launchd to fire 2026-05-04 09:00 local. Self-removes after success.

Pattern:
  - PlainEmail enforces no-jargon (Rule 16 hardwire).
  - Threshold = 7 sessions ("warmup gate" in code, deliberately not in copy).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Resolve sibling watchdog/ directory regardless of caller cwd
WATCHDOG_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(WATCHDOG_DIR))

from email_send import PlainEmail, send  # noqa: E402

PATS_NAME = "POLYMARKET_TRADING_3.0"
PATS_FRIENDLY = "PATS-Copy"
WARMUP_TARGET = 7
DB = WATCHDOG_DIR / "history.db"


def count_pats_sessions() -> int:
    if not DB.is_file():
        return 0
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE project = ?", (PATS_NAME,)
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def build_email(count: int) -> PlainEmail:
    if count >= WARMUP_TARGET:
        return PlainEmail(
            subject=f"PATS-Copy watchdog is fully active",
            body=(
                f"Good news. The watchdog has now seen {count} PATS-Copy sessions, "
                f"which is enough for it to know what your normal looks like. "
                f"From this point on, the trend signals — cost going up, sessions "
                f"taking longer than usual, more corrections than usual — are live "
                f"for PATS, not just the safety alerts that were already on."
            ),
            what_to_do=(
                f"Reply 'help' to your watchdog bot on Telegram to see the "
                f"current PATS-Copy numbers, or run this in Terminal: "
                f"python3 ~/claude-hq/watchdog/watchdog.py --assess --project {PATS_NAME}"
            ),
            severity="info",
        )
    else:
        remaining = WARMUP_TARGET - count
        return PlainEmail(
            subject=f"PATS-Copy watchdog still warming up ({count} of {WARMUP_TARGET})",
            body=(
                f"Quick check on PATS-Copy: the watchdog has captured {count} "
                f"of the {WARMUP_TARGET} sessions it needs before it can spot "
                f"trend changes. {remaining} more sessions in PATS and the "
                f"trend signals will switch on. Safety alerts (reverts, plan-skipping, "
                f"repeated mistakes) are already live — those don't need a "
                f"warm-up period."
            ),
            what_to_do=(
                f"Nothing to do — just keep working in PATS as normal. The "
                f"counter will tick up automatically. If you want to peek at "
                f"the count yourself, run: sqlite3 ~/claude-hq/watchdog/history.db "
                f"'SELECT COUNT(*) FROM sessions WHERE project=\"{PATS_NAME}\"'"
            ),
            severity="info",
        )


def main() -> int:
    count = count_pats_sessions()
    email = build_email(count)
    result = send(email)
    if result.get("ok"):
        print(f"sent — {count} PATS sessions captured")
        return 0
    print(f"send failed — {result.get('error', 'unknown error')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
