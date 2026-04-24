#!/usr/bin/env python3
"""
HQ Watchdog — self-evolution engine.

Runs weekly (Sundays 08:00 by default). Looks at recent alert history, proposes
tweaks, and sends them to Telegram as lettered options you can approve with a
short reply.

Three-zone evolution model (from commander/LESSONS.md Rule 16 + watchdog/README):
  ZONE A  Auto  — rolling baselines, known-flake suppression, session-type
                  normalisation. Logged to LEARNINGS.md, no approval needed.
  ZONE B  Propose — suggested threshold tweaks or new metrics. Sent to you via
                  Telegram. Applied only after you approve.
  ZONE C  Never  — cannot silence critical alerts, cannot raise thresholds on
                  safety metrics, cannot modify its own Python code.

Also handles:
  --daily   : the plain-language morning digest
  --weekly  : the self-improvement proposal digest
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from telegram import PlainAlert, send as send_telegram  # noqa: E402

WATCHDOG_DIR = Path(__file__).parent.resolve()
HISTORY_DB = WATCHDOG_DIR / "history.db"
LEARNINGS_MD = WATCHDOG_DIR / "LEARNINGS.md"

# -----------------------------------------------------------------------------
# Protected metrics — Zone C (watchdog cannot self-modify these)
# -----------------------------------------------------------------------------

PROTECTED_METRICS = {
    "git_revert_on_claude_hq",
    "trust_gate_overrides",
    "lessons_rule_velocity",
    "repeated_mistake_signal",
    "mission_board_before_agents",
}


# -----------------------------------------------------------------------------
# Daily digest
# -----------------------------------------------------------------------------

def send_daily_digest() -> dict:
    """Brief morning check-in. Always plain English, always short."""
    conn = _db()
    yesterday_start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_sessions = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(correction_count),0) AS c "
        "FROM sessions WHERE session_date = ?",
        (yesterday_start,),
    ).fetchone()
    yesterday_commits = conn.execute(
        "SELECT COUNT(*) AS n FROM commits WHERE commit_date LIKE ?",
        (f"{yesterday_start}%",),
    ).fetchone()["n"]
    conn.close()

    n_sessions = yesterday_sessions["n"] or 0
    n_corrections = yesterday_sessions["c"] or 0
    n_commits = yesterday_commits or 0

    if n_sessions == 0 and n_commits == 0:
        alert = PlainAlert(
            what_happened=(
                "Yesterday was a quiet day for HQ — no sessions, no commits. "
                "Nothing to report."
            ),
            what_to_do="Nothing to do right now.",
            severity="info",
            headline_emoji="☀️",
        )
    else:
        tone = "all good" if n_corrections == 0 else "worth a look"
        corr_phrase = (
            "no corrections from you" if n_corrections == 0
            else f"{n_corrections} correction{'s' if n_corrections != 1 else ''} from you"
        )
        alert = PlainAlert(
            what_happened=(
                f"Yesterday: {n_sessions} session{'s' if n_sessions != 1 else ''}, "
                f"{corr_phrase}, {n_commits} commit{'s' if n_commits != 1 else ''} "
                f"landed on claude-hq. Overall — {tone}."
            ),
            what_to_do=(
                "Nothing to do right now."
                if n_corrections == 0
                else 'reply "show" if you want me to pull the sessions where you made corrections.'
            ),
            severity="info",
            headline_emoji="☀️",
        )

    return send_telegram(alert)


# -----------------------------------------------------------------------------
# Weekly self-improvement proposals
# -----------------------------------------------------------------------------

def send_weekly_digest() -> dict:
    """Propose tweaks based on the past week's alert history."""
    proposals = _gather_proposals()

    if not proposals:
        alert = PlainAlert(
            what_happened=(
                "Weekly check-in — nothing to propose this week. Alerts are firing at "
                "a sensible rate and the watchdog hasn't spotted anything worth tweaking."
            ),
            what_to_do="Nothing to do right now.",
            severity="info",
            headline_emoji="🧠",
        )
        return send_telegram(alert)

    lines = [
        "I'd like to make the following small changes based on what I've seen this week:",
        "",
    ]
    for letter, prop in zip("ABCDEFGHIJ", proposals):
        lines.append(f"{letter}) {prop['headline']}")
        lines.append(f"   {prop['reason']}")
        lines.append("")

    what_happened = "\n".join(lines).strip()
    letters = "".join(letter for letter, _ in zip("ABCDEFGHIJ", proposals))
    what_to_do = (
        f"Reply {' / '.join(list(letters))} to approve one, '{letters}' for all, "
        f"or 'skip' to reject."
    )

    alert = PlainAlert(
        what_happened=what_happened,
        what_to_do=what_to_do,
        severity="info",
        headline_emoji="🧠",
    )
    return send_telegram(alert)


def _gather_proposals() -> list[dict[str, Any]]:
    """Collect Zone-B proposals from last 7 days of data."""
    conn = _db()
    since = (datetime.now() - timedelta(days=7)).isoformat()
    proposals: list[dict[str, Any]] = []

    # Proposal 1: noisy metrics with low true-positive rate
    # Approximation: lots of alerts sent on the same metric in a short window
    noisy = conn.execute(
        """SELECT metric_id, COUNT(*) AS alerts
           FROM scores
           WHERE computed_at >= ? AND alert_sent = 1 AND severity = 'warn'
           GROUP BY metric_id HAVING alerts > 5""",
        (since,),
    ).fetchall()

    for row in noisy:
        if row["metric_id"] in PROTECTED_METRICS:
            continue
        proposals.append({
            "headline": f"Quieter alerts on '{_plain_name(row['metric_id'])}'",
            "reason": (
                f"I've raised this alert {row['alerts']} times this week. "
                f"That's a lot of noise — worth making it less twitchy."
            ),
            "change": {
                "kind": "threshold_increase",
                "metric": row["metric_id"],
                "rationale": f"{row['alerts']} alerts in 7 days",
            },
        })

    # Proposal 2: session-type normalisation
    # If a metric tends to be high only on sessions with many files_modified,
    # propose context-aware comparison. Simple heuristic: stdev of metric
    # value across sessions > 2x the mean.
    # Skipped in MVP — placeholder for future evolution.

    conn.close()
    return proposals


# -----------------------------------------------------------------------------
# LEARNINGS.md logging
# -----------------------------------------------------------------------------

def log_learning(zone: str, action: str, rationale: str, reversal: str) -> None:
    """Append to LEARNINGS.md with clear reversal instructions."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = (
        f"\n## {timestamp} [{zone}] {action}\n"
        f"   Rationale: {rationale}\n"
        f"   Reversal: {reversal}\n"
    )
    with LEARNINGS_MD.open("a", encoding="utf-8") as f:
        f.write(entry)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _plain_name(metric_id: str) -> str:
    """Map metric_id to plain-language name for digest use."""
    mapping = {
        "subagents_per_task": "how many helpers Commander calls in",
        "tokens_per_task": "how much thinking per task",
        "user_corrections_per_session": "how often you correct Commander",
        "messages_per_completed_task": "messages needed per task",
        "session_duration_to_first_commit": "time to get started",
    }
    return mapping.get(metric_id, metric_id.replace("_", " "))


def main() -> int:
    parser = argparse.ArgumentParser(description="HQ Watchdog evolution engine")
    parser.add_argument("--daily", action="store_true", help="Send the daily morning digest")
    parser.add_argument("--weekly", action="store_true", help="Send the weekly self-improvement digest")
    args = parser.parse_args()

    if args.daily:
        result = send_daily_digest()
        print(json.dumps(result))
        return 0 if result.get("ok") else 1

    if args.weekly:
        result = send_weekly_digest()
        print(json.dumps(result))
        return 0 if result.get("ok") else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
