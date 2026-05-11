#!/usr/bin/env python3
"""
Runtime rule: Branch 2 shadow-mode health.

Watches the PolygonBlockListener + DivergenceLogger pair while the bot runs
with BLOCK_LISTENER_ENABLED=true (Phase 6 shadow validation window).

Four checks rolled into one SSH session for efficiency:

  1. ws-disconnected         — WS dropped >5 min and no http-fallback line either
  2. no-blocks               — no PolygonBlockListener-attributed block lines >10 min
                              (Polygon blocks every ~2s, anything quiet for >10 min
                               means the listener is wedged)
  3. divergence-recall-low   — most recent Divergence summary shows WS recall <95%
                              (promotion threshold per master handoff)
  4. divergence-latency-slow — most recent Divergence summary shows median WS-vs-REST
                              delta worse than +5000ms (i.e. WS is SLOWER than REST)

Behaviour outside the shadow window:

  When the bot has not logged 'Branch 2 shadow listener: ENABLED' since the most
  recent restart, the rule exits silently — no findings, no audit noise. Re-arms
  automatically when the flag is flipped on.

Usage:
    python rules/runtime/branch2_shadow_health.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit

RULE_PREFIX = "pats-runtime-branch2"

# Look-back windows
SSH_HOST = "root@204.168.204.247"
LOG_LINES = 8000  # last ~8k lines of pm2 output (~30-60 min of activity)
WS_DROP_WINDOW_MIN = 5
NO_BLOCK_WINDOW_MIN = 10
RECALL_THRESHOLD = 0.95
LATENCY_THRESHOLD_MS = 5000  # WS-vs-REST median delta worse than +5s = WS slower

# Log signatures emitted by the bot
SIG_LISTENER_ENABLED = "Branch 2 shadow listener: ENABLED"
SIG_WS_CONNECTED = re.compile(r"PolygonBlockListener: WS connected")
SIG_WS_RECONNECT = re.compile(r"PolygonBlockListener: WS error")
SIG_HTTP_FALLBACK = re.compile(r"PolygonBlockListener: WS exhausted")
SIG_BLOCK_PROCESSED = re.compile(r"PolygonBlockListener: block (\d+) →")
SIG_DIVERGENCE_SUMMARY = re.compile(
    r"Divergence summary \[.*?\]: total=(\d+) matched=(\d+) rest-only=(\d+) ws-only=(\d+) "
    r"ws-recall=([\d.]+%|n/a) median-delta\(ws-rest\)=(-?\d+ms|n/a) pending=\d+",
)
# pm2 log line preface: "0|polymark | 2026-05-08 19:14:10:" — extract the timestamp
TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def fetch_pm2_logs(lines: int = LOG_LINES) -> list[str]:
    """Pull the last N lines of polymarket-bot pm2 logs via SSH."""
    try:
        out = subprocess.run(
            [
                "ssh", "-o", "ConnectTimeout=10", SSH_HOST,
                f"cd /opt/polymarket-bot && pm2 logs polymarket-bot --nostream --lines {lines} 2>&1",
            ],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if out.returncode != 0:
            return []
        return out.stdout.splitlines()
    except (subprocess.TimeoutExpired, OSError):
        return []


def parse_log_ts(line: str) -> datetime | None:
    m = TIMESTAMP_RE.search(line)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def latest_match_ts(lines: list[str], pattern: re.Pattern[str]) -> datetime | None:
    for line in reversed(lines):
        if pattern.search(line):
            return parse_log_ts(line)
    return None


def main() -> int:
    lines = fetch_pm2_logs()
    if not lines:
        # Couldn't reach server — orchestrator handles transient SSH failures elsewhere
        return 0

    # Gate: is the shadow listener actually enabled?
    if not any(SIG_LISTENER_ENABLED in line for line in lines):
        # Flag is off (or hasn't been seen since the log window we pulled). Silent exit.
        return 0

    now = datetime.now(timezone.utc)

    # ── Check 1: WS disconnect lasting >WS_DROP_WINDOW_MIN min ───────────────
    last_connect = latest_match_ts(lines, SIG_WS_CONNECTED)
    last_fallback = latest_match_ts(lines, SIG_HTTP_FALLBACK)
    last_error = latest_match_ts(lines, SIG_WS_RECONNECT)

    # If last error is more recent than last connect AND there's no fallback line either,
    # AND the gap is bigger than the threshold → flag.
    if (
        last_error is not None
        and (last_connect is None or last_error > last_connect)
        and (last_fallback is None or last_error > last_fallback)
        and now - last_error > timedelta(minutes=WS_DROP_WINDOW_MIN)
    ):
        emit(Finding(
            rule_id=f"{RULE_PREFIX}.ws-disconnected",
            severity="warn",
            what_happened=(
                f"The Branch 2 block listener has been disconnected from the Polygon "
                f"WebSocket for more than {WS_DROP_WINDOW_MIN} minutes and hasn't "
                f"switched to its HTTP polling fallback either. Branch 2 is currently "
                f"blind, which means the shadow comparison against the existing REST "
                f"monitor is missing data."
            ),
            what_to_do=(
                "Look at recent pm2 logs for 'PolygonBlockListener' lines to see the "
                "error chain, and consider restarting polymarket-bot. If the WSS host "
                "(publicnode.com) is the problem, the listener should auto-fall-back "
                "to HTTP polling — if it didn't, the fallback wiring is broken."
            ),
            technical_detail={
                "last_ws_error_utc": last_error.isoformat(),
                "last_ws_connect_utc": last_connect.isoformat() if last_connect else None,
                "last_http_fallback_utc": last_fallback.isoformat() if last_fallback else None,
                "minutes_since_error": round((now - last_error).total_seconds() / 60, 1),
            },
        ))

    # ── Check 2: no blocks processed in NO_BLOCK_WINDOW_MIN min ──────────────
    last_block_ts = latest_match_ts(lines, SIG_BLOCK_PROCESSED)
    if last_block_ts is not None and now - last_block_ts > timedelta(minutes=NO_BLOCK_WINDOW_MIN):
        emit(Finding(
            rule_id=f"{RULE_PREFIX}.no-blocks",
            severity="warn",
            what_happened=(
                f"The Branch 2 block listener hasn't reported any new Polygon blocks "
                f"for over {NO_BLOCK_WINDOW_MIN} minutes. Polygon produces a block "
                f"every ~2 seconds, so a quiet window this long means either the "
                f"listener has stalled or the watched-wallet list is empty (no traffic "
                f"to surface)."
            ),
            what_to_do=(
                "Confirm the leaderboard scraper is updating watcher lists "
                "(grep 'Leaderboard update' in pm2 logs). If watcher lists are healthy, "
                "the listener is wedged — restart polymarket-bot. The shadow comparison "
                "will resume on its own once blocks start flowing again."
            ),
            technical_detail={
                "last_block_processed_utc": last_block_ts.isoformat(),
                "minutes_since_last_block": round((now - last_block_ts).total_seconds() / 60, 1),
            },
        ))

    # ── Checks 3 & 4: most-recent Divergence summary ─────────────────────────
    summary = None
    for line in reversed(lines):
        m = SIG_DIVERGENCE_SUMMARY.search(line)
        if m:
            summary = m
            break

    if summary is not None:
        total = int(summary.group(1))
        matched = int(summary.group(2))
        # groups 3 (rest_only) and 4 (ws_only) intentionally not parsed —
        # they would only feed the disabled divergence-recall-low check below.
        recall_str = summary.group(5)
        delta_str = summary.group(6)

        # ─── divergence-recall-low DISABLED 2026-05-11 ─────────────────────
        # The 'recall' metric assumes REST/data-api is ground truth. CTDD
        # forensic on 2026-05-10 proved this is wrong: data-api filters
        # certain trades for unknown reasons, so a low recall % doesn't
        # actually indicate WS missing trades — it indicates REST not
        # showing trades that WS correctly detected.
        #
        # Verified in 2026-05-11 50-trade test: WS catches 100% of REST's
        # trades AND additional trades data-api doesn't index. The rule
        # firing produces alert noise on a structurally invalid premise.
        #
        # Replacement options under consideration (not yet built):
        # - WS-side coverage check against on-chain ground truth
        # - Per-pipeline detection-rate health (once Branch 3 lands)
        #
        # For now: this sub-check is disabled. Other sub-checks remain
        # active: ws-disconnected, no-blocks, divergence-latency-slow.
        # ───────────────────────────────────────────────────────────────────
        # if recall_str.endswith("%") and total >= 20:
        #     recall = float(recall_str.rstrip("%")) / 100.0
        #     if recall < RECALL_THRESHOLD:
        #         emit(Finding(...))
        _ = recall_str  # silence unused-variable lint while the block is disabled

        if delta_str.endswith("ms") and total >= 20:
            delta_ms = int(delta_str.rstrip("ms"))
            # Positive delta = WS arrived AFTER REST = WS is slower
            if delta_ms > LATENCY_THRESHOLD_MS:
                emit(Finding(
                    rule_id=f"{RULE_PREFIX}.divergence-latency-slow",
                    severity="info",
                    what_happened=(
                        f"The Branch 2 WebSocket listener is currently slower than the "
                        f"existing REST monitor by about {delta_ms / 1000:.1f} seconds "
                        f"on average. The whole reason for switching to a block "
                        f"listener is faster detection, so this number should be "
                        f"strongly negative (WS faster). A positive number means "
                        f"something is delaying the decoder pipeline."
                    ),
                    what_to_do=(
                        "Check whether the WSS endpoint is healthy and whether the "
                        "decoder is keeping up with block traffic. Polygon produces "
                        "many matchOrders txs per block — if decoding is CPU-bound, "
                        "consider sampling or moving decode to a worker thread."
                    ),
                    technical_detail={
                        "median_delta_ms": delta_ms,
                        "threshold_ms": LATENCY_THRESHOLD_MS,
                        "matched_pairs": matched,
                    },
                ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
