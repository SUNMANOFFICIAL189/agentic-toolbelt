#!/usr/bin/env python3
"""
Runtime rule: Paperclip server liveness.

Probes the /health endpoint. If unreachable, emits a critical Finding —
no other rule can run meaningfully when the server is down, so this rule
is the most important of the set.

Read-only — never mutates Paperclip state.

Usage:
    python rules/runtime/server_health.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.paperclip_api import PAPERCLIP_URL, get_health

RULE_ID = "paperclip-runtime-server-health"


def main() -> int:
    health = get_health()
    if health is None:
        finding = Finding(
            rule_id=RULE_ID,
            severity="critical",
            what_happened=(
                "The Paperclip server stopped answering the watchdog. The watchdog tried to "
                "reach it and got nothing back. Either the server crashed, the laptop is "
                "asleep, or something killed the process."
            ),
            what_to_do=(
                "Open a terminal and run: launchctl list | grep paperclip — if there's no "
                "'com.fleet.paperclip' line, the server is gone. Restart it with: "
                "launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fleet.paperclip.plist"
            ),
            technical_detail={
                "rule_id": RULE_ID,
                "url": PAPERCLIP_URL,
                "endpoint": "/health",
                "result": "unreachable",
            },
        )
        emit(finding)
        return 0

    # Healthy — emit info finding so we have a positive signal in audit.log
    # for trend analysis. Soak mode logs it; active mode skips info-severity.
    finding = Finding(
        rule_id=f"{RULE_ID}.alive",
        severity="info",
        what_happened="The Paperclip server answered the watchdog. Nothing to worry about.",
        what_to_do="No action needed.",
        technical_detail={
            "rule_id": f"{RULE_ID}.alive",
            "url": PAPERCLIP_URL,
            "health_response_keys": sorted(list(health.keys())) if isinstance(health, dict) else None,
        },
    )
    emit(finding)
    return 0


if __name__ == "__main__":
    sys.exit(main())
