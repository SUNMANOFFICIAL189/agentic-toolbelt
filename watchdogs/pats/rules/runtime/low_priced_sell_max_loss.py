#!/usr/bin/env python3
"""
Runtime rule: low-priced SELL max-loss exposure.

For Polymarket SELL positions, max-loss = (1 - entry_price) * shares,
where shares = our_size / entry_price. This is heavily asymmetric for
low-priced YES tokens: a $75 SELL at entry 0.04 carries up to $1,800
max-loss exposure (24x the position dollar amount).

Position sizer treats max-loss as if it equals our_size. True for BUY,
false for SELL. This rule flags any open SELL where the asymmetric max-
loss exceeds the configured fraction of current portfolio balance (defaults
to 5%, matching the bot's MAX_LOSS_PCT_PER_TRADE env var as of 2026-05-08).

Calibrated against 2026-05-07 finding: a $75 SELL at entry 0.041 closed
for -$943 in a single event when the side-aware stop-loss surfaced the
accumulated tail risk. Phase A → BACKLOG → this rule.

Usage:
    python rules/runtime/low_priced_sell_max_loss.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.supabase import query

RULE_ID = "pats-runtime-low-priced-sell-max-loss"
import os as _os
# Read from env to stay aligned with the bot's MAX_LOSS_PCT_PER_TRADE.
# Default 0.05 (5%) matches the SELL-aware sizing recalibration shipped at
# PATS-Copy commit 935d44f. If the bot's env diverges from this default
# the watchdog should be re-pointed via this same env var.
MAX_LOSS_FRACTION = float(_os.environ.get("MAX_LOSS_PCT_PER_TRADE", "0.05") or "0.05")
INITIAL_BALANCE_FALLBACK = 6300.0


def main() -> int:
    balance = _fetch_current_balance()
    cap = MAX_LOSS_FRACTION * balance

    rows = query(
        "copy_trades",
        select="id,market_id,leader_wallet,side,our_size,our_entry_price,leader_entry_price,entry_time",
        filters={
            "status": "in.(open,pending)",
            "side": "eq.sell",
        },
        limit=200,
    )

    flagged = []
    for r in rows:
        entry = r.get("our_entry_price") or r.get("leader_entry_price") or 0.0
        size = r.get("our_size") or 0.0
        if entry <= 0 or size <= 0:
            continue
        shares = size / entry
        max_loss = (1.0 - entry) * shares
        if max_loss > cap:
            flagged.append({
                "id": r["id"],
                "market_id": r["market_id"],
                "entry_price": entry,
                "our_size": size,
                "max_loss_dollars": round(max_loss, 2),
                "max_loss_pct_of_balance": round(max_loss / balance * 100, 2),
            })

    if not flagged:
        return 0

    sample = flagged[0]
    count = len(flagged)
    finding = Finding(
        rule_id=RULE_ID,
        severity="critical",
        what_happened=(
            f"The bot has {count} open SELL position(s) that could lose more than "
            f"{MAX_LOSS_FRACTION * 100:.1f}% of the portfolio if the bet goes against us. The biggest one: "
            f"\"{sample['market_id'][:50]}\" entered at {sample['entry_price']:.4f}, "
            f"could lose ${sample['max_loss_dollars']:.0f} "
            f"({sample['max_loss_pct_of_balance']:.1f}% of portfolio)."
        ),
        what_to_do=(
            "Check the BACKLOG item 'PATS-Copy: SELL-aware position sizing' and "
            "decide whether to manually close the flagged position(s) or wait. "
            "Long-term fix is the sizer change — open SELLs at low prices should "
            "be capped by max-loss, not just dollar amount."
        ),
        technical_detail={
            "rule_id": RULE_ID,
            "balance": balance,
            "cap_dollars": round(cap, 2),
            "max_loss_fraction": MAX_LOSS_FRACTION,
            "flagged_count": count,
            "flagged": flagged,
        },
    )
    emit(finding)
    return 0


def _fetch_current_balance() -> float:
    """Read .bot-status.json from the server via SSH. Fall back to initial balance."""
    import subprocess
    try:
        out = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "root@204.168.204.247",
             "cat /opt/polymarket-bot/.bot-status.json"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            data = json.loads(out.stdout)
            return float(data.get("balance", INITIAL_BALANCE_FALLBACK))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
        pass
    return INITIAL_BALANCE_FALLBACK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        # Network errors → exit 0, no finding (orchestrator handles transient failures)
        print(f"# transient: supabase unreachable: {e}", file=sys.stderr)
        sys.exit(0)
