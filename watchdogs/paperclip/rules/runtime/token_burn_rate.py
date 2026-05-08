#!/usr/bin/env python3
"""
Runtime rule: token burn rate spike detection.

Catches the 2026-04-28 incident shape — sustained high tokens-per-minute
across the Paperclip fleet that depletes the Anthropic 5-hour Max-plan
budget faster than the user expects. Paperclip's per-month budgets won't
catch this (different time window).

Reads the configured companies' window-spend endpoint and computes a
short-window burn rate. Emits warn/critical based on tokens/minute over
the last 5 minutes.

Calibration (from 2026-04-28 post-mortem):
  Incident peak: ~2.2M tokens/min sustained for ~30 minutes (66M total)
  Normal idle:   <50K tokens/min (heartbeats only)
  Normal active: 100-300K tokens/min (real work)

Thresholds:
  warn     >  500K tokens/min sustained over 5 minutes
  critical > 2.0M tokens/min sustained over 5 minutes (incident-level)

Config (env vars, read at run time):
    PAPERCLIP_COMPANY_IDS  — comma-separated UUIDs to monitor.
                             If unset, falls back to the Agent Alpha company
                             ID baked into paperclip-burn-tracker.py
                             (58684871-fb90-4f3a-bf30-bbf80f2677e1).

Usage:
    python rules/runtime/token_burn_rate.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.paperclip_api import _get  # noqa: PLC2701 — intentional internal helper reuse

RULE_ID = "paperclip-runtime-token-burn-rate"
WINDOW_MINUTES = 5
WARN_TOKENS_PER_MIN = 500_000
CRITICAL_TOKENS_PER_MIN = 2_000_000

DEFAULT_COMPANY_ID = "58684871-fb90-4f3a-bf30-bbf80f2677e1"  # Agent Alpha — UGC Ads


def _company_ids() -> list[str]:
    raw = os.environ.get("PAPERCLIP_COMPANY_IDS", "").strip()
    if raw:
        return [c.strip() for c in raw.split(",") if c.strip()]
    return [DEFAULT_COMPANY_ID]


def _window_spend(company_id: str, minutes: int) -> dict | None:
    """GET /companies/:id/costs/window-spend?windowMinutes=N. None if unavailable."""
    return _get(f"/companies/{company_id}/costs/window-spend?windowMinutes={minutes}")


def main() -> int:
    for company_id in _company_ids():
        data = _window_spend(company_id, WINDOW_MINUTES)
        if data is None:
            emit(Finding(
                rule_id=f"{RULE_ID}.unreachable",
                severity="info",
                what_happened=(
                    f"The watchdog couldn't read the recent spend for company {company_id[:8]}…. "
                    "Either the server is down (server_health rule will catch that) or this "
                    "company ID doesn't exist anymore."
                ),
                what_to_do=(
                    "If server_health is also failing, fix that first. Otherwise check "
                    "PAPERCLIP_COMPANY_IDS in the watchdog environment matches a real company."
                ),
                technical_detail={"rule_id": f"{RULE_ID}.unreachable", "company_id": company_id},
            ))
            continue

        # Response shape per server/src/services/costs.ts: { totalTokens, totalCents, ... }
        # Use a tolerant lookup — Paperclip's exact field names may evolve.
        total_tokens = (
            data.get("totalTokens")
            or data.get("tokens")
            or data.get("total_tokens")
            or 0
        )
        try:
            total_tokens = int(total_tokens)
        except (TypeError, ValueError):
            total_tokens = 0

        if total_tokens <= 0:
            # No spend in window — that's fine, no finding needed
            continue

        per_minute = total_tokens // WINDOW_MINUTES

        if per_minute >= CRITICAL_TOKENS_PER_MIN:
            emit(Finding(
                rule_id=f"{RULE_ID}.critical",
                severity="critical",
                what_happened=(
                    f"Paperclip is burning tokens at roughly {per_minute:,} per minute right now "
                    f"(measured over the last {WINDOW_MINUTES} minutes). This is the same shape "
                    "as the 2026-04-28 incident that ate 91 percent of the daily quota overnight. "
                    "If this keeps up, you'll be locked out of the bigger Claude models in well "
                    "under an hour."
                ),
                what_to_do=(
                    "Pause the running agents immediately: open Paperclip, find the agents on "
                    "this company, and click pause on each. Then check why they're firing — "
                    "usually it's a stuck loop, not real work."
                ),
                technical_detail={
                    "rule_id": f"{RULE_ID}.critical",
                    "company_id": company_id,
                    "tokens_per_minute": per_minute,
                    "window_minutes": WINDOW_MINUTES,
                    "total_tokens_in_window": total_tokens,
                },
            ))
        elif per_minute >= WARN_TOKENS_PER_MIN:
            emit(Finding(
                rule_id=f"{RULE_ID}.warn",
                severity="warn",
                what_happened=(
                    f"Paperclip's burning tokens faster than the usual active rate — about "
                    f"{per_minute:,} per minute over the last {WINDOW_MINUTES} minutes. Not yet "
                    "incident-level, but worth a glance to confirm there's real work driving it."
                ),
                what_to_do=(
                    "Open Paperclip's costs view for this company. If you see one agent dominating "
                    "and you don't recognise what it's doing, pause it."
                ),
                technical_detail={
                    "rule_id": f"{RULE_ID}.warn",
                    "company_id": company_id,
                    "tokens_per_minute": per_minute,
                    "window_minutes": WINDOW_MINUTES,
                    "total_tokens_in_window": total_tokens,
                },
            ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
