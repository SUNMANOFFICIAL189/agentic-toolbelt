#!/usr/bin/env python3
"""
HQ Watchdog — Telegram listener.

Polls Telegram for messages from the authorised chat ID and dispatches
to a strict command allowlist. Runs via launchd every 30 seconds.

Security model:
  * Only commands from TELEGRAM_CHAT_ID are accepted. Anything else is
    silently dropped (and audit-logged).
  * Tier 1 (read-only): rules, sessions, security, cost, status, help
  * Tier 2 (safe actions): pause, resume, quiet, mute, unmute, check
  * Tier 3 (code/system actions) is NOT implemented. Any future Tier 3
    capability requires explicit design + confirmation flow.
  * Rate-limited to 20 commands per minute across all sources.
  * Every command, reply, and error is written to watchdog/audit.log.
  * No arbitrary shell execution — every command is a named verb mapped
    to a specific function.

Runs once per launchd tick. Fetches new updates since last seen,
processes them, saves the new high-water mark, exits. launchd
re-invokes on StartInterval (default 30s).
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent))
from telegram import _build_ssl_context, get_credentials  # noqa: E402
import reminders as reminders_mod  # type: ignore  # noqa: E402
# Local import — Pyright may resolve to the PyPI `watchdog` pkg, so type: ignore.
from watchdog import (  # type: ignore  # noqa: E402
    cli_rules, cli_sessions, cli_security, cli_cost, assess_and_alert,
)

WATCHDOG_DIR = Path(__file__).parent.resolve()
STATE_FILE = WATCHDOG_DIR / "runtime_state.json"
AUDIT_LOG = WATCHDOG_DIR / "audit.log"
LAST_UPDATE_FILE = WATCHDOG_DIR / ".last_update_id"

TELEGRAM_MAX_CHARS = 3500  # real limit is 4096 — leave headroom

# Read-only CLI commands (Tier 1)
TIER1_CLI = {"rules", "sessions", "security", "cost"}

# Tier 1 info commands
TIER1_INFO = {"help", "status"}

# Tier 2 safe-action commands
TIER2_ACTIONS = {"pause", "resume", "quiet", "mute", "unmute", "check"}

ALL_COMMANDS = TIER1_CLI | TIER1_INFO | TIER2_ACTIONS

# Protected metrics cannot be muted
PROTECTED_METRICS = {
    "git_revert",
    "trust_gate_overrides",
    "lessons_rule_velocity",
    "repeated_mistake_signal",
    "mission_board_before_agents",
}

METRIC_ALIASES = {
    "rules": "lessons_rule_velocity",
    "cost": "tokens_per_task",
    "tokens": "tokens_per_task",
    "corrections": "user_corrections_per_session",
    "helpers": "subagents_per_task",
    "subagents": "subagents_per_task",
    "timing": "session_duration_to_first_commit",
    "duration": "session_duration_to_first_commit",
    "messages": "messages_per_completed_task",
    "security": "trust_gate_overrides",
    "reverts": "git_revert",
}

# Preferred display name for each metric_id (primary alias, used in status output)
PRIMARY_ALIAS = {
    "lessons_rule_velocity": "rules",
    "tokens_per_task": "cost",
    "user_corrections_per_session": "corrections",
    "subagents_per_task": "helpers",
    "session_duration_to_first_commit": "timing",
    "messages_per_completed_task": "messages",
    "trust_gate_overrides": "security",
    "git_revert": "reverts",
}


# -----------------------------------------------------------------------------
# State + audit helpers
# -----------------------------------------------------------------------------

def audit(line: str) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    try:
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{ts}  {line}\n")
    except OSError:
        pass  # never crash on audit failure


def load_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"paused": False, "quiet_until": None, "muted_metrics": []}
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"paused": False, "quiet_until": None, "muted_metrics": []}


def save_state(state: dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except OSError as e:
        audit(f"ERROR save_state: {e}")


def load_last_update_id() -> int:
    if not LAST_UPDATE_FILE.is_file():
        return 0
    try:
        return int(LAST_UPDATE_FILE.read_text().strip())
    except (OSError, ValueError):
        return 0


def save_last_update_id(n: int) -> None:
    try:
        LAST_UPDATE_FILE.write_text(str(n))
    except OSError as e:
        audit(f"ERROR save_last_update_id: {e}")


# -----------------------------------------------------------------------------
# Telegram I/O
# -----------------------------------------------------------------------------

def fetch_updates(token: str, offset: int) -> list[dict[str, Any]]:
    url = (
        f"https://api.telegram.org/bot{token}/getUpdates"
        f"?offset={offset}&timeout=5&allowed_updates=%5B%22message%22%5D"
    )
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10, context=_build_ssl_context()) as r:
            body = json.loads(r.read().decode("utf-8"))
            if not body.get("ok"):
                audit(f"getUpdates not-ok: {body}")
                return []
            return body.get("result", [])
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        audit(f"getUpdates NETWORK: {e}")
        return []
    except Exception as e:  # noqa: BLE001
        audit(f"getUpdates UNEXPECTED: {type(e).__name__}: {e}")
        return []


def send_reply(token: str, chat_id: str, text: str) -> bool:
    """Send a plain-text reply. Long outputs wrapped in <pre> for legibility."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # If it looks like tabular/formatted output, wrap in <pre>
    if "\n" in safe and ("  " in safe or "|" in safe):
        safe = f"<pre>{safe}</pre>"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": safe[:TELEGRAM_MAX_CHARS + 500],  # small buffer for <pre> tags
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_build_ssl_context()) as r:
            body = json.loads(r.read().decode("utf-8"))
            ok = bool(body.get("ok"))
            if not ok:
                audit(f"sendMessage not-ok: {body}")
            return ok
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        audit(f"sendMessage NETWORK: {e}")
        return False
    except Exception as e:  # noqa: BLE001
        audit(f"sendMessage UNEXPECTED: {type(e).__name__}: {e}")
        return False


# -----------------------------------------------------------------------------
# Command handlers
# -----------------------------------------------------------------------------

def parse_command(text: str) -> tuple[str, list[str]]:
    tokens = text.strip().lower().split()
    if not tokens:
        return "", []
    # Strip common leading punctuation
    cmd = tokens[0].lstrip("/!.,:")
    return cmd, tokens[1:]


def parse_duration(s: str) -> Optional[timedelta]:
    """Parse '2h', '30m', '45min', '1hour'. Returns None if unparseable."""
    m = re.match(r"^(\d+)\s*(h|hour|hours|m|min|minute|minutes)?$", s.lower())
    if not m:
        return None
    n, unit = int(m.group(1)), (m.group(2) or "h").lower()
    if unit.startswith("h"):
        return timedelta(hours=n)
    return timedelta(minutes=n)


def cmd_help() -> str:
    return (
        "Commands I understand:\n"
        "\n"
        "📊 See info:\n"
        "   rules      recent LESSONS additions\n"
        "   sessions   recent sessions with numbers\n"
        "   security   reverts + Trust Gate overrides\n"
        "   cost       cost/efficiency snapshot\n"
        "   status     quick current state\n"
        "\n"
        "🔕 Control alerts:\n"
        "   pause      silence warn-level alerts until you resume\n"
        "   resume     re-enable alerts\n"
        "   quiet 2h   snooze alerts for 2 hours (also: 30m, 1h, etc.)\n"
        "   mute rules silence one metric (rules / cost / corrections / helpers / timing / messages)\n"
        "   unmute rules turn a muted metric back on\n"
        "\n"
        "▶️ Trigger:\n"
        "   check      run a fresh assessment now\n"
        "\n"
        "Critical alerts (reverts, trust-gate overrides, repeat-mistakes) still\n"
        "fire through pause / quiet / mute — at most once per hour."
    )


def cmd_status(state: dict[str, Any]) -> str:
    lines: list[str] = []
    if state.get("paused"):
        lines.append("🔕 Currently paused. Reply 'resume' to re-enable warn-level alerts.")
    elif state.get("quiet_until"):
        lines.append(f"🔕 Quiet until {state['quiet_until'][:16]}.")
    else:
        lines.append("✓ Listening for alerts.")

    muted = state.get("muted_metrics") or []
    if muted:
        names: list[str] = []
        for m in muted:
            if m in PROTECTED_METRICS:
                continue
            display = PRIMARY_ALIAS.get(m) or m or "?"
            names.append(display)
        if names:
            lines.append(f"Muted: {', '.join(sorted(set(names)))}")

    lines.append("")
    lines.append("Reply 'help' for the list of commands.")
    return "\n".join(lines)


def cmd_cli(verb: str) -> str:
    """Call the CLI helper directly with plain=True so Telegram gets conversational prose."""
    funcs = {
        "rules": cli_rules,
        "sessions": cli_sessions,
        "security": cli_security,
        "cost": cli_cost,
    }
    fn = funcs.get(verb)
    if not fn:
        return f"I don't know how to handle '{verb}'."
    try:
        result = fn(plain=True)
        if len(result) > TELEGRAM_MAX_CHARS:
            result = result[:TELEGRAM_MAX_CHARS] + "\n\n… (truncated — the full detail is available if you run it locally)"
        return result
    except Exception as e:  # noqa: BLE001
        audit(f"cmd_cli ERROR '{verb}': {type(e).__name__}: {e}")
        return f"Something went wrong running '{verb}'. The audit log has the details."


def cmd_check() -> str:
    """Run a fresh assessment and describe the outcome in plain English."""
    try:
        outcomes = assess_and_alert()
    except Exception as e:  # noqa: BLE001
        audit(f"cmd_check ERROR: {type(e).__name__}: {e}")
        return "Couldn't run a fresh assessment. The audit log has the details."

    actions = {o["action"] for o in outcomes}
    if actions <= {"quiet", "warmup"}:
        return "Ran a fresh check — everything's within normal ranges. Nothing to flag."

    lines = ["Ran a fresh check. Here's what stood out:", ""]
    for o in outcomes:
        action = o.get("action", "?")
        if action in ("quiet", "warmup"):
            continue
        metric = PRIMARY_ALIAS.get(o.get("metric", ""), o.get("metric", "?"))
        reason = o.get("reason", "")
        if action == "sent":
            lines.append(f"• Sent alert about {metric}: {reason}")
        elif action == "suppressed":
            lines.append(f"• {metric} still flagged but suppressed (you've already been told).")
        elif action == "failed":
            lines.append(f"• Tried to send alert about {metric} but it didn't get through.")
        else:
            lines.append(f"• {metric}: {action} — {reason}")
    return "\n".join(lines)


def cmd_pause(state: dict[str, Any]) -> str:
    state["paused"] = True
    state["quiet_until"] = None
    save_state(state)
    return (
        "🔕 Alerts paused. Warn-level alerts are silenced until you reply 'resume'.\n"
        "Critical alerts (reverts, trust-gate overrides) still fire — at most once per hour."
    )


def cmd_resume(state: dict[str, Any]) -> str:
    state["paused"] = False
    state["quiet_until"] = None
    save_state(state)
    return "✓ Alerts resumed. You'll hear from me when something's worth flagging."


def cmd_quiet(args: list[str], state: dict[str, Any]) -> str:
    if not args:
        return "Say how long, e.g. 'quiet 2h' or 'quiet 30m'."
    duration = parse_duration(args[0])
    if not duration:
        return f"I didn't understand '{args[0]}'. Try '2h' or '30m'."
    until = datetime.now() + duration
    state["paused"] = False
    state["quiet_until"] = until.isoformat(timespec="seconds")
    save_state(state)
    return (
        f"🔕 Quiet until {until.strftime('%H:%M')}.\n"
        "Critical alerts still fire — at most once per hour."
    )


def cmd_mute(args: list[str], state: dict[str, Any]) -> str:
    if not args:
        return "Say which metric, e.g. 'mute cost' or 'mute helpers'."
    alias = args[0].lower()
    metric_id = METRIC_ALIASES.get(alias)
    if not metric_id:
        known = ", ".join(sorted(set(METRIC_ALIASES.keys())))
        return f"I don't know a metric called '{alias}'. Known: {known}."
    if metric_id in PROTECTED_METRICS:
        return (
            f"'{alias}' is a protected metric — I can't mute it from Telegram.\n"
            "Protected metrics cover reverts, Trust Gate overrides, and repeat mistakes —\n"
            "these should always reach you."
        )
    muted = state.setdefault("muted_metrics", [])
    if metric_id in muted:
        return f"'{alias}' is already muted. Reply 'unmute {alias}' to turn it back on."
    muted.append(metric_id)
    save_state(state)
    return f"🔕 Muted '{alias}'. Reply 'unmute {alias}' to turn it back on."


def cmd_unmute(args: list[str], state: dict[str, Any]) -> str:
    if not args:
        return "Say which metric, e.g. 'unmute cost'."
    alias = args[0].lower()
    metric_id = METRIC_ALIASES.get(alias)
    if not metric_id:
        return f"I don't know a metric called '{alias}'."
    muted = state.get("muted_metrics", [])
    if metric_id not in muted:
        return f"'{alias}' is not currently muted."
    muted.remove(metric_id)
    save_state(state)
    return f"✓ Unmuted '{alias}'."


# -----------------------------------------------------------------------------
# Rate limiting
# -----------------------------------------------------------------------------

RATE_LIMIT_FILE = WATCHDOG_DIR / ".rate_limit.json"
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit() -> bool:
    """Return True if within limit, False if exceeded."""
    now = datetime.now().timestamp()
    history: list[float] = []
    if RATE_LIMIT_FILE.is_file():
        try:
            history = json.loads(RATE_LIMIT_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            history = []
    # Drop entries outside window
    history = [t for t in history if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(history) >= RATE_LIMIT_MAX:
        return False
    history.append(now)
    try:
        RATE_LIMIT_FILE.write_text(json.dumps(history))
    except OSError:
        pass
    return True


# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------

def dispatch(cmd: str, args: list[str], state: dict[str, Any]) -> str:
    if cmd == "help":
        return cmd_help()
    if cmd == "status":
        return cmd_status(state)
    if cmd in TIER1_CLI:
        return cmd_cli(cmd)
    if cmd == "pause":
        return cmd_pause(state)
    if cmd == "resume":
        return cmd_resume(state)
    if cmd == "quiet":
        return cmd_quiet(args, state)
    if cmd == "mute":
        return cmd_mute(args, state)
    if cmd == "unmute":
        return cmd_unmute(args, state)
    if cmd == "check":
        return cmd_check()
    return f"I don't understand '{cmd}'. Reply 'help' for the list of commands."


def _check_reminders_safely() -> None:
    """Fire any due reminders. Safe wrapper — never crashes the listener."""
    try:
        reminders_mod.check_and_fire()
    except Exception as e:  # noqa: BLE001
        audit(f"reminder check ERROR: {type(e).__name__}: {e}")


def main() -> int:
    # Reminder check runs first — independent of Telegram updates.
    # If TG credentials are missing or there are no updates, reminders still fire.
    _check_reminders_safely()

    token, chat_id = get_credentials()
    if not token or not chat_id:
        audit("listener: telegram credentials not found, exiting (reminders still ran)")
        return 0  # not an error — reminders may still be working
    chat_id_str = str(chat_id)

    state = load_state()
    last_id = load_last_update_id()
    updates = fetch_updates(token, last_id + 1)

    if not updates:
        return 0

    for update in updates:
        update_id = update.get("update_id", 0)
        if update_id > last_id:
            last_id = update_id

        msg = update.get("message") or {}
        text = (msg.get("text") or "").strip()
        from_chat = str((msg.get("chat") or {}).get("id", ""))

        # Authorisation check — hard allowlist on chat_id
        if from_chat != chat_id_str:
            audit(f"DROPPED message from unauthorized chat {from_chat}: {text[:40]!r}")
            continue

        # Rate limit
        if not check_rate_limit():
            audit(f"RATE-LIMITED: {text[:40]!r}")
            send_reply(token, chat_id_str,
                       "Too many commands too quickly. Take a breath and try again in a minute.")
            continue

        cmd, args = parse_command(text)
        if not cmd:
            continue  # ignore empty
        if cmd not in ALL_COMMANDS:
            audit(f"unknown cmd: {text[:60]!r}")
            send_reply(token, chat_id_str,
                       f"I don't understand '{text[:40]}'. Reply 'help' for the command list.")
            continue

        audit(f"cmd: {cmd} args={args}")
        try:
            reply = dispatch(cmd, args, state)
        except Exception as e:  # noqa: BLE001
            reply = "Something went wrong handling that. Check audit.log."
            audit(f"DISPATCH ERROR {cmd}: {type(e).__name__}: {e}")
        ok = send_reply(token, chat_id_str, reply)
        audit(f"reply sent={ok} for cmd={cmd}")

    save_last_update_id(last_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
