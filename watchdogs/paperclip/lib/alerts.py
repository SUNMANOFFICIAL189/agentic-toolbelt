"""
Adapter: Paperclip watchdog Finding → HQ Watchdog PlainAlert → Telegram send.

Reuses the existing plain-language enforcement in ~/claude-hq/watchdog/telegram.py
(Lesson 16). Severity, what_happened, what_to_do map 1:1.

All alerts are prefixed with [Paperclip] in the headline so multi-tenant
HQ Watchdog Telegram threads stay legible alongside PATS findings.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `from telegram import ...` without polluting sys.path globally
_HQ_WATCHDOG = Path.home() / "claude-hq" / "watchdog"
if str(_HQ_WATCHDOG) not in sys.path:
    sys.path.insert(0, str(_HQ_WATCHDOG))

from telegram import PlainAlert, send  # type: ignore[import-not-found]

from .finding import Finding


def to_plain_alert(finding: Finding) -> PlainAlert:
    """Wrap a Finding's user-facing fields as a [Paperclip]-tagged PlainAlert."""
    return PlainAlert(
        what_happened=f"[Paperclip] {finding.what_happened}",
        what_to_do=finding.what_to_do,
        severity=finding.severity,
    )


def send_finding(finding: Finding) -> dict:
    """Send the finding as a Telegram alert. Returns the API response dict."""
    return send(to_plain_alert(finding))


__all__ = ["to_plain_alert", "send_finding"]
