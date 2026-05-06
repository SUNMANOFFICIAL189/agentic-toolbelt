#!/usr/bin/env python3
"""
HQ Watchdog — Telegram sender with HARDWIRED plain-language enforcement.

All user-facing alerts go through PlainAlert, which requires two fields:
  - what_happened: plain-English description
  - what_to_do:    one concrete instruction

Any alert containing banned jargon is rejected before send. Technical detail
stays in logs and history.db — it never reaches Sunil's phone.

Reference: commander/LESSONS.md Rule 16, watchdog/STYLE_GUIDE.md
Pattern ported from: ~/Desktop/POLYMARKET_TRADING_3.0/src/utils/telegram.ts
Secrets via Keychain: commander/LESSONS.md Rule 15
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _build_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that works on macOS stock Python.

    Python's default cert path on macOS often points at a missing file
    (/Library/Frameworks/Python.framework/.../etc/openssl/cert.pem). We
    prefer the certifi bundle when available — it ships with most modern
    Python distributions and contains the Mozilla CA set.
    """
    try:
        import certifi  # type: ignore[import-not-found]
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()

# -----------------------------------------------------------------------------
# Hardwired banned-word list (the jargon linter)
# -----------------------------------------------------------------------------

BANNED_WORDS: tuple[str, ...] = (
    # statistical
    "threshold", "baseline delta", "rolling mean", "rolling window",
    "stdev", "std dev", "z-score", "percentile", "quantile",
    "p-value", "correlation", "variance", "coefficient", "sigma",
    # ML / data-science
    "regression detected", "anomaly detected", "drift detected",
    "fp/tp", "false positive", "true positive", "fpr", "tpr",
    # units / shorthand
    "7d", "24h", "1h", "5m", "n=", "sd=",
    # engineering
    "throughput", "latency", "concurrency", "idempotent",
    "subagents_per_task", "tokens_per_task",  # raw metric IDs
    # alert labels
    " warn:", " crit:", " info:", "[warn]", "[crit]", "[info]",
)

# Allow these headline emoji+labels (plain-English ok)
ALLOWED_HEADLINE_LABELS: tuple[str, ...] = (
    "something's off", "something just went wrong", "heads up",
    "all good", "morning check", "weekly tune-up",
    "things are getting slower", "connected", "disconnected",
)


class JargonError(ValueError):
    """Raised when an alert contains banned technical language."""


# -----------------------------------------------------------------------------
# PlainAlert — the ONLY way alerts leave this module
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PlainAlert:
    """A user-facing alert. Both fields are REQUIRED and must pass linting."""

    what_happened: str
    what_to_do: str
    severity: str = "info"  # info | warn | critical
    headline_emoji: str = ""

    def __post_init__(self) -> None:
        if not self.what_happened or not self.what_happened.strip():
            raise JargonError("what_happened is required and cannot be empty")
        if not self.what_to_do or not self.what_to_do.strip():
            raise JargonError("what_to_do is required and cannot be empty")
        if self.severity not in {"info", "warn", "critical"}:
            raise JargonError(f"severity must be info|warn|critical, got {self.severity!r}")

        _lint_text(self.what_happened, field="what_happened")
        _lint_text(self.what_to_do, field="what_to_do")

        action_markers = (
            "reply ", "run ", "run:", "open ", "do this:", "check ",
            "nothing to do", "no action",
        )
        if not any(m in self.what_to_do.lower() for m in action_markers):
            raise JargonError(
                "what_to_do must contain a concrete action verb "
                "(run/open/reply/check/do this:) or explicitly say 'nothing to do'. "
                f"Got: {self.what_to_do[:80]!r}"
            )

    def to_telegram_markdown(self) -> str:
        """Render to a Telegram-ready HTML string."""
        emoji = self.headline_emoji or _default_emoji(self.severity)
        return (
            f"{emoji} <b>{_headline_for(self.severity)}</b>\n\n"
            f"{self.what_happened}\n\n"
            f"<i>What to do:</i> {self.what_to_do}"
        )


def _lint_text(text: str, field: str) -> None:
    """Raise JargonError if text contains banned words."""
    lowered = text.lower()
    hits = [w for w in BANNED_WORDS if w in lowered]
    if hits:
        raise JargonError(
            f"{field} contains banned jargon: {hits}. "
            f"Rewrite using plain English. See watchdog/STYLE_GUIDE.md."
        )


def _default_emoji(severity: str) -> str:
    return {"info": "☀️", "warn": "🤔", "critical": "🚨"}[severity]


def _headline_for(severity: str) -> str:
    return {
        "info": "HQ update",
        "warn": "Heads up",
        "critical": "Something just went wrong",
    }[severity]


# -----------------------------------------------------------------------------
# Credential retrieval — Keychain only, following Rule 15
# -----------------------------------------------------------------------------

def _keychain_get(service_name: str) -> Optional[str]:
    """Read a secret from macOS Keychain. Returns None if missing."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ["USER"], "-s", service_name, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, KeyError, FileNotFoundError):
        return None


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Lightweight .env parser (no external deps)."""
    data: dict[str, str] = {}
    if not env_path.is_file():
        return data
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def get_credentials() -> tuple[Optional[str], Optional[str]]:
    """Return (bot_token, chat_id). None if either is missing."""
    env_path = Path(__file__).parent / ".env"
    env = _load_env_file(env_path)
    token_key = env.get("TELEGRAM_TOKEN_KEYCHAIN", "claude-hq-watchdog-token")
    chat_key = env.get("TELEGRAM_CHAT_ID_KEYCHAIN", "claude-hq-watchdog-chat-id")
    return _keychain_get(token_key), _keychain_get(chat_key)


# -----------------------------------------------------------------------------
# Send path
# -----------------------------------------------------------------------------

def send(alert: PlainAlert) -> dict:
    """
    Send a PlainAlert to Telegram. Returns {'ok': bool, 'error': str|None}.

    Fire-and-forget in spirit: never raises on network errors, but DOES raise
    JargonError if the alert failed linting (that must be caught before code
    ships — silently dropping a malformed alert would hide bugs).

    Linting already happened in PlainAlert.__post_init__. Re-linting here is
    defence-in-depth for any code path that constructs PlainAlert by non-
    standard means.
    """
    _lint_text(alert.what_happened, field="what_happened")
    _lint_text(alert.what_to_do, field="what_to_do")

    token, chat_id = get_credentials()
    if not token or not chat_id:
        return {
            "ok": False,
            "error": "Telegram credentials not found in Keychain. See watchdog/README.md Step 3.",
        }

    payload = {
        "chat_id": chat_id,
        "text": alert.to_telegram_markdown(),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        ctx = _build_ssl_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return {"ok": True, "error": None}
            return {"ok": False, "error": f"Telegram API returned not-ok: {body}"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Network error: {e.reason}"}
    except Exception as e:  # noqa: BLE001 - last-resort safety net
        return {"ok": False, "error": f"Unexpected: {type(e).__name__}: {e}"}


# -----------------------------------------------------------------------------
# Self-test (python3 telegram.py --self-test)
# -----------------------------------------------------------------------------

def _self_test() -> int:
    print("HQ Watchdog — Telegram self-test")
    print()

    # 1. Linter should REJECT a jargon-laden alert
    try:
        PlainAlert(
            what_happened="WARN: subagents_per_task regression exceeded threshold (baseline delta +78%)",
            what_to_do="Reply 'show'",
            severity="warn",
        )
        print("  ❌ FAIL: linter accepted jargon alert (should have rejected)")
        return 1
    except JargonError as e:
        print(f"  ✓ Linter correctly rejected jargon alert")
        print(f"    reason: {str(e)[:120]}")

    # 2. Linter should ACCEPT a plain-English alert
    try:
        plain = PlainAlert(
            what_happened=(
                "Good news — the alert pipe is working. You'll start getting daily "
                "quality digests at 08:00 once the baseline week is complete."
            ),
            what_to_do="Nothing to do right now.",
            severity="info",
            headline_emoji="✅",
        )
        print(f"  ✓ Linter accepted plain-English alert")
    except JargonError as e:
        print(f"  ❌ FAIL: linter rejected plain alert: {e}")
        return 1

    # 3. Check credentials
    token, chat_id = get_credentials()
    if not token:
        print("  ⚠ TELEGRAM_BOT_TOKEN not found in Keychain.")
        print("    Run: security add-generic-password -U -a \"$USER\" \\")
        print("             -s \"claude-hq-watchdog-token\" -w \"<YOUR_BOT_TOKEN>\"")
        return 2
    if not chat_id:
        print("  ⚠ TELEGRAM_CHAT_ID not found in Keychain.")
        print("    Run: security add-generic-password -U -a \"$USER\" \\")
        print("             -s \"claude-hq-watchdog-chat-id\" -w \"<YOUR_CHAT_ID>\"")
        return 2
    print(f"  ✓ Credentials found in Keychain (token length {len(token)}, chat_id set)")

    # 4. Send test alert
    print()
    print("Sending test alert to your Telegram…")
    result = send(plain)
    if result["ok"]:
        print("  ✓ Sent successfully — check your Telegram.")
        print()
        print("Expected message:")
        print()
        print(plain.to_telegram_markdown())
        return 0
    else:
        print(f"  ❌ FAIL: {result['error']}")
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="HQ Watchdog Telegram sender")
    parser.add_argument("--self-test", action="store_true", help="Run the end-to-end self-test")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
