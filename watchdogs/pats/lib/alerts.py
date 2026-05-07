"""
Adapter: PATS watchdog Finding → HQ Watchdog PlainAlert → Telegram send.

Reuses the existing plain-language enforcement in ~/claude-hq/watchdog/telegram.py
(Lesson 16). Severity, what_happened, what_to_do map 1:1.

Static rule findings (semgrep) carry developer-targeted text in the rule's
.message field; we translate those into plain-English PlainAlerts via a
template table indexed by check_id, NOT by passing the semgrep message
directly through (would trip the jargon linter).
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
    """Wrap a Finding's user-facing fields as a PlainAlert."""
    return PlainAlert(
        what_happened=finding.what_happened,
        what_to_do=finding.what_to_do,
        severity=finding.severity,
    )


def send_finding(finding: Finding) -> dict:
    """Send the finding as a Telegram alert. Returns the API response dict."""
    return send(to_plain_alert(finding))


# ---------------------------------------------------------------------------
# Static rule plain-English template table
# ---------------------------------------------------------------------------
# Maps semgrep check_id → (severity, what_happened_template, what_to_do_template).
# Templates use {path}, {line}, {count}.

_STATIC_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "pats-trade-missing-enddate": (
        "warn",
        "The bot's code has {count} place(s) where a position is created without "
        "an end-date being attached. Without an end-date, the lifecycle manager "
        "falls back to a 24-hour timeout instead of the market's real resolution date. "
        "First example: {path} line {line}.",
        "Open {path} at line {line} and add the end-date field to the position object "
        "(e.g. `endDate: input.endDate`). The 730a85f and f80fd08 commits show the pattern.",
    ),
    "pats-side-blind-loss-formula": (
        "critical",
        "The bot's stop-loss math may not be checking whether a trade is a buy or a sell. "
        "Found {count} suspect place(s). On 2026-05-07 this exact bug class let one SELL "
        "ride from 4 cents to 55 cents before the stop fired, costing the bot 943 dollars. "
        "First example: {path} line {line}.",
        "Open {path} at line {line} and wrap the loss calculation in a buy-versus-sell "
        "check, or delegate to risk-manager.calculatePnl which already handles both sides.",
    ),
    "pats-copy-executor-receiving-signal-bot": (
        "warn",
        "The bot may be loading signal-bot trades into the copy-trader pool — they should "
        "live in the signal executor only. Found {count} suspect place(s). On 2026-05-07 "
        "this caused duplicate position alerts because the close went to the wrong pool. "
        "First example: {path} line {line}.",
        "Open {path} at line {line} and filter signal-bot trades out of the rows before "
        "passing them to copyExecutor.hydrateOpenTrades. The c0e44b9 commit shows the pattern.",
    ),
    "pats-missing-await-closeposition": (
        "critical",
        "The bot's code may have an async close-position call that isn't being awaited. "
        "Found {count} place(s). When this happens, the variable holds a Promise that's "
        "always truthy, so the next 'if' check always passes and silently masks the trade "
        "close. On 2026-05-07 this exact pattern caused the database to record a real "
        "$943 loss as zero. First example: {path} line {line}.",
        "Open {path} at line {line} and add 'await' before the closePosition call. "
        "The enclosing function may need to become async too. Commit 58d8257 shows the fix.",
    ),
}


def static_finding_from_semgrep(check_id: str, path: str, line: int, count: int) -> Finding:
    """Build a plain-English Finding from a semgrep result (or aggregate of results).

    `check_id` is the rule id semgrep prints (last segment of the dotted name);
    `path` and `line` come from the first/representative finding;
    `count` is total findings for this rule across the run.
    """
    short_id = check_id.split(".")[-1]
    if short_id in _STATIC_TEMPLATES:
        severity, wh_template, wd_template = _STATIC_TEMPLATES[short_id]
    else:
        severity = "warn"
        wh_template = (
            "The watchdog flagged {count} place(s) in the bot's code matching rule '{rule}'. "
            "First example: {path} line {line}."
        )
        wd_template = "Open {path} at line {line} and review the rule guidance in the .yml file."

    fmt = {"path": path, "line": line, "count": count, "rule": short_id}
    return Finding(
        rule_id=f"pats-static-{short_id}",
        severity=severity,
        what_happened=wh_template.format(**fmt),
        what_to_do=wd_template.format(**fmt),
        technical_detail={
            "check_id": check_id,
            "path": path,
            "line": line,
            "count": count,
        },
    )


__all__ = ["to_plain_alert", "send_finding", "static_finding_from_semgrep"]
