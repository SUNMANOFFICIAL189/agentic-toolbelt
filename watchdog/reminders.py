#!/usr/bin/env python3
"""
HQ Watchdog — reminder engine.

Schedules milestone reminders to fire on a specific date/time, via email
or Telegram. Edge-triggered: each reminder fires exactly once. Channel is
per-reminder so different milestones can use different paths.

State lives in watchdog/reminders.json — JSON list of reminder objects.
The listener calls check_and_fire() on every tick (~30s) so reminders
fire within 30 seconds of their fire_at time.

Reminder schema:
{
  "id": "phase-0-day-3-rpi-nudge",   // unique, used for log + dedup
  "fire_at": "2026-04-27T08:00:00",  // ISO datetime, local time
  "channel": "email" | "telegram",
  "severity": "info" | "warn" | "critical",
  "subject": "...",                  // becomes email subject or TG headline
  "body": "...",                     // plain English, Rule 16 enforced
  "what_to_do": "...",               // one concrete action
  "sent": false,
  "sent_at": null,
  "error": null
}
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent))
from email_send import PlainEmail, send as send_email  # type: ignore  # noqa: E402
from telegram import PlainAlert, send as send_telegram  # noqa: E402

WATCHDOG_DIR = Path(__file__).parent.resolve()
REMINDERS_FILE = WATCHDOG_DIR / "reminders.json"
AUDIT_LOG = WATCHDOG_DIR / "audit.log"


# -----------------------------------------------------------------------------
# Persistence
# -----------------------------------------------------------------------------

def _audit(line: str) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    try:
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{ts}  reminders: {line}\n")
    except OSError:
        pass


def load_reminders() -> list[dict[str, Any]]:
    if not REMINDERS_FILE.is_file():
        return []
    try:
        data = json.loads(REMINDERS_FILE.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "reminders" in data:
            return data["reminders"]
        return []
    except (OSError, json.JSONDecodeError) as e:
        _audit(f"load ERROR: {e}")
        return []


def save_reminders(reminders: list[dict[str, Any]]) -> None:
    try:
        REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))
    except OSError as e:
        _audit(f"save ERROR: {e}")


# -----------------------------------------------------------------------------
# Schema validation
# -----------------------------------------------------------------------------

REQUIRED_FIELDS = ("id", "fire_at", "channel", "subject", "body", "what_to_do")
ALLOWED_CHANNELS = {"email", "telegram"}
ALLOWED_SEVERITIES = {"info", "warn", "critical"}


@dataclass(frozen=True)
class ValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def validate(reminder: dict[str, Any]) -> Optional[str]:
    """Return None if valid, error string if not."""
    for f in REQUIRED_FIELDS:
        if not reminder.get(f):
            return f"missing required field: {f}"
    if reminder["channel"] not in ALLOWED_CHANNELS:
        return f"channel must be one of {ALLOWED_CHANNELS}, got {reminder['channel']!r}"
    sev = reminder.get("severity", "info")
    if sev not in ALLOWED_SEVERITIES:
        return f"severity must be one of {ALLOWED_SEVERITIES}, got {sev!r}"
    try:
        datetime.fromisoformat(reminder["fire_at"])
    except (TypeError, ValueError):
        return f"fire_at must be ISO datetime, got {reminder['fire_at']!r}"
    return None


# -----------------------------------------------------------------------------
# Send paths
# -----------------------------------------------------------------------------

def _fire_email(reminder: dict[str, Any]) -> dict[str, Any]:
    """Send the reminder via email. Returns {ok, error}."""
    try:
        email = PlainEmail(
            subject=reminder["subject"],
            body=reminder["body"],
            what_to_do=reminder["what_to_do"],
            severity=reminder.get("severity", "info"),
        )
    except Exception as e:  # JargonError or similar
        return {"ok": False, "error": f"PlainEmail rejected: {e}"}
    return send_email(email)


def _fire_telegram(reminder: dict[str, Any]) -> dict[str, Any]:
    """Send the reminder via Telegram. Returns {ok, error}."""
    try:
        # Combine subject + body into a single TG message
        what_happened = f"{reminder['subject']}\n\n{reminder['body']}"
        alert = PlainAlert(
            what_happened=what_happened,
            what_to_do=reminder["what_to_do"],
            severity=reminder.get("severity", "info"),
        )
    except Exception as e:
        return {"ok": False, "error": f"PlainAlert rejected: {e}"}
    return send_telegram(alert)


# -----------------------------------------------------------------------------
# Main entry — called by listener
# -----------------------------------------------------------------------------

def check_and_fire(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Walk reminders, fire any whose fire_at <= now and sent is false.

    Returns a list of outcomes for caller logging / debugging:
      [{"id": str, "action": "sent"|"suppressed"|"failed", "reason": str}, ...]
    """
    if now is None:
        now = datetime.now()

    reminders = load_reminders()
    if not reminders:
        return []

    outcomes: list[dict[str, Any]] = []
    changed = False

    for r in reminders:
        rid = r.get("id", "<no-id>")
        if r.get("sent"):
            continue

        err = validate(r)
        if err:
            _audit(f"INVALID {rid}: {err}")
            outcomes.append({"id": rid, "action": "invalid", "reason": err})
            continue

        try:
            fire_at = datetime.fromisoformat(r["fire_at"])
        except ValueError:
            outcomes.append({"id": rid, "action": "invalid", "reason": "bad fire_at"})
            continue

        if now < fire_at:
            continue  # not yet

        # Fire it
        channel = r["channel"]
        if channel == "email":
            result = _fire_email(r)
        elif channel == "telegram":
            result = _fire_telegram(r)
        else:
            result = {"ok": False, "error": f"unknown channel {channel!r}"}

        ok = bool(result.get("ok"))
        r["sent"] = ok
        r["sent_at"] = now.isoformat(timespec="seconds") if ok else None
        r["error"] = None if ok else result.get("error")
        changed = True

        action = "sent" if ok else "failed"
        reason = "" if ok else (result.get("error") or "")
        _audit(f"{action} {rid} via {channel}: {reason}")
        outcomes.append({"id": rid, "action": action, "reason": reason})

    if changed:
        save_reminders(reminders)

    return outcomes


# -----------------------------------------------------------------------------
# CLI helpers — used from listener and from terminal
# -----------------------------------------------------------------------------

def cli_list() -> str:
    reminders = load_reminders()
    if not reminders:
        return "No reminders scheduled."

    lines = [f"Scheduled reminders ({len(reminders)} total):", ""]
    for r in reminders:
        rid = r.get("id", "?")
        fire_at = r.get("fire_at", "?")
        channel = r.get("channel", "?")
        sent = r.get("sent")
        status = "✓ sent" if sent else "⏳ pending"
        if sent and r.get("sent_at"):
            status += f" at {r['sent_at'][:16]}"
        elif r.get("error"):
            status = f"❌ failed ({r['error'][:60]})"
        lines.append(f"  {status:30} {fire_at[:16]}  [{channel}]  {rid}")
    return "\n".join(lines)


def cli_add(rid: str, fire_at: str, subject: str, body: str, what_to_do: str,
            channel: str = "email", severity: str = "info") -> str:
    reminders = load_reminders()
    if any(r.get("id") == rid for r in reminders):
        return f"Reminder with id '{rid}' already exists. Use a different id."
    new = {
        "id": rid, "fire_at": fire_at, "channel": channel, "severity": severity,
        "subject": subject, "body": body, "what_to_do": what_to_do,
        "sent": False, "sent_at": None, "error": None,
    }
    err = validate(new)
    if err:
        return f"Invalid: {err}"
    reminders.append(new)
    save_reminders(reminders)
    return f"Added reminder '{rid}' for {fire_at} via {channel}."


def cli_forget(rid: str) -> str:
    reminders = load_reminders()
    before = len(reminders)
    reminders = [r for r in reminders if r.get("id") != rid]
    if len(reminders) == before:
        return f"No reminder with id '{rid}' found."
    save_reminders(reminders)
    return f"Removed reminder '{rid}'."


def cli_test_in(minutes: int = 2, channel: str = "email") -> str:
    """Schedule a quick test reminder N minutes from now."""
    fire_at = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
    return cli_add(
        rid=f"test-{int(datetime.now().timestamp())}",
        fire_at=fire_at,
        subject=f"Test reminder ({channel} pipe)",
        body=(
            f"This is a test of the HQ Watchdog reminder system. "
            f"You should receive this about {minutes} minutes after it was scheduled."
        ),
        what_to_do="Nothing to do — if you got this, the pipe works.",
        channel=channel,
        severity="info",
    )


# -----------------------------------------------------------------------------
# CLI dispatch
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="HQ Watchdog reminders")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="Show all scheduled reminders")

    p_check = sub.add_parser("check", help="Check + fire any due reminders now")
    p_check.add_argument("--quiet", action="store_true", help="Suppress per-reminder output")

    p_test = sub.add_parser("test", help="Schedule a quick test reminder")
    p_test.add_argument("--minutes", type=int, default=2, help="Fire after N minutes (default 2)")
    p_test.add_argument("--channel", default="email", choices=["email", "telegram"])

    p_forget = sub.add_parser("forget", help="Remove a reminder by id")
    p_forget.add_argument("id", help="Reminder id to remove")

    args = parser.parse_args()

    if args.cmd == "list":
        print(cli_list())
        return 0
    if args.cmd == "check":
        outcomes = check_and_fire()
        if not args.quiet:
            for o in outcomes:
                print(f"  [{o['action']}] {o['id']}: {o['reason']}")
        return 0
    if args.cmd == "test":
        print(cli_test_in(args.minutes, args.channel))
        return 0
    if args.cmd == "forget":
        print(cli_forget(args.id))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
