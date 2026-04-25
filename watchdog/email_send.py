#!/usr/bin/env python3
"""
HQ Watchdog — email sender with HARDWIRED plain-language enforcement.

All user-facing emails go through PlainEmail, which requires three fields:
  - subject:  plain-English subject line
  - body:     plain-English body
  - what_to_do: one concrete instruction

Any email containing banned jargon is rejected before send. Same Rule 16
hardwire as the Telegram path — if it can't reach a non-technical reader
at a glance, it doesn't go.

Reference: commander/LESSONS.md Rule 16, watchdog/STYLE_GUIDE.md
Pattern mirrors: watchdog/telegram.py PlainAlert
Secrets via Keychain: commander/LESSONS.md Rule 15

Module is named email_send.py (not email.py) to avoid shadowing Python's
stdlib `email` package.
"""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import subprocess
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

# Same banned-word list as telegram.py — kept in sync via Rule 16
sys.path.insert(0, str(Path(__file__).parent))
from telegram import JargonError, _lint_text  # noqa: E402

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

DEFAULT_FROM_KEYCHAIN = "claude-hq-watchdog-smtp-user"
DEFAULT_PASSWORD_KEYCHAIN = "claude-hq-watchdog-smtp-password"
DEFAULT_TO_KEYCHAIN = "claude-hq-watchdog-email-to"


# -----------------------------------------------------------------------------
# PlainEmail — the ONLY way emails leave this module
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PlainEmail:
    """A user-facing email. All three fields are required and must pass linting."""

    subject: str
    body: str
    what_to_do: str
    severity: str = "info"  # info | warn | critical

    def __post_init__(self) -> None:
        if not self.subject or not self.subject.strip():
            raise JargonError("subject is required and cannot be empty")
        if not self.body or not self.body.strip():
            raise JargonError("body is required and cannot be empty")
        if not self.what_to_do or not self.what_to_do.strip():
            raise JargonError("what_to_do is required and cannot be empty")
        if self.severity not in {"info", "warn", "critical"}:
            raise JargonError(f"severity must be info|warn|critical, got {self.severity!r}")
        if len(self.subject) > 200:
            raise JargonError(f"subject too long ({len(self.subject)} chars, max 200)")

        _lint_text(self.subject, field="subject")
        _lint_text(self.body, field="body")
        _lint_text(self.what_to_do, field="what_to_do")

        # Soft-require an action verb in what_to_do (same as PlainAlert)
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

    def to_email_message(self, from_addr: str, to_addr: str) -> EmailMessage:
        """Render to an EmailMessage ready for SMTP send."""
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg["Subject"] = self._subject_with_emoji()
        msg.set_content(self._render_body())
        return msg

    def _subject_with_emoji(self) -> str:
        emoji = {"info": "🔔", "warn": "⚠️", "critical": "🚨"}[self.severity]
        return f"{emoji} HQ — {self.subject}"

    def _render_body(self) -> str:
        return (
            f"{self.body}\n\n"
            f"---\n"
            f"What to do: {self.what_to_do}\n\n"
            f"---\n"
            f"Sent by HQ Watchdog (~/claude-hq/watchdog/).\n"
            f"To stop these, edit ~/claude-hq/watchdog/reminders.json or "
            f"reply 'pause' on Telegram."
        )


# -----------------------------------------------------------------------------
# Credential retrieval — Keychain only
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


def get_credentials() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (smtp_user, smtp_password, to_addr). None for any missing."""
    return (
        _keychain_get(DEFAULT_FROM_KEYCHAIN),
        _keychain_get(DEFAULT_PASSWORD_KEYCHAIN),
        _keychain_get(DEFAULT_TO_KEYCHAIN),
    )


# -----------------------------------------------------------------------------
# Send path
# -----------------------------------------------------------------------------

def send(email: PlainEmail, to_override: Optional[str] = None) -> dict:
    """
    Send a PlainEmail via Gmail SMTP. Returns {'ok': bool, 'error': str|None}.

    Re-runs the linter as defence-in-depth even though PlainEmail.__post_init__
    already did. Any code path that constructs PlainEmail by non-standard means
    cannot bypass the jargon gate.
    """
    _lint_text(email.subject, field="subject")
    _lint_text(email.body, field="body")
    _lint_text(email.what_to_do, field="what_to_do")

    from_addr, password, to_addr = get_credentials()
    if to_override:
        to_addr = to_override
    if not from_addr or not password:
        return {
            "ok": False,
            "error": (
                "SMTP credentials not in Keychain. Need entries for "
                f"'{DEFAULT_FROM_KEYCHAIN}' and '{DEFAULT_PASSWORD_KEYCHAIN}'."
            ),
        }
    if not to_addr:
        return {
            "ok": False,
            "error": (
                f"Destination address not set. Add a Keychain entry for "
                f"'{DEFAULT_TO_KEYCHAIN}' or pass to_override."
            ),
        }

    msg = email.to_email_message(from_addr, to_addr)

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls(context=ctx)
            server.login(from_addr, password)
            server.send_message(msg)
        return {"ok": True, "error": None}
    except smtplib.SMTPAuthenticationError as e:
        return {"ok": False, "error": f"Auth failed (check app password): {e}"}
    except smtplib.SMTPException as e:
        return {"ok": False, "error": f"SMTP error: {type(e).__name__}: {e}"}
    except (TimeoutError, OSError) as e:
        return {"ok": False, "error": f"Network: {type(e).__name__}: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"Unexpected: {type(e).__name__}: {e}"}


# -----------------------------------------------------------------------------
# Self-test
# -----------------------------------------------------------------------------

def _self_test() -> int:
    print("HQ Watchdog — Email self-test")
    print()

    # 1. Linter rejects jargon
    try:
        PlainEmail(
            subject="WARN: regression detected in baseline",
            body="Threshold exceeded by 78% over rolling window.",
            what_to_do="run watchdog --sessions",
        )
        print("  ❌ FAIL: linter accepted jargon email")
        return 1
    except JargonError:
        print("  ✓ Linter rejected jargon email")

    # 2. Linter accepts plain English
    try:
        plain = PlainEmail(
            subject="Email pipe is working",
            body=(
                "Good news — the HQ Watchdog can now send you email reminders. "
                "You'll receive scheduled milestone pings on your phone whenever "
                "they fire."
            ),
            what_to_do="Nothing to do right now.",
            severity="info",
        )
        print("  ✓ Linter accepted plain-English email")
    except JargonError as e:
        print(f"  ❌ FAIL: linter rejected plain email: {e}")
        return 1

    # 3. Credentials present?
    user, password, to_addr = get_credentials()
    missing = []
    if not user:
        missing.append(f"'{DEFAULT_FROM_KEYCHAIN}' (your Gmail address)")
    if not password:
        missing.append(f"'{DEFAULT_PASSWORD_KEYCHAIN}' (16-char app password)")
    if not to_addr:
        missing.append(f"'{DEFAULT_TO_KEYCHAIN}' (where to send — usually same as from)")
    if missing:
        print(f"  ⚠ Keychain missing: {', '.join(missing)}")
        print(f"    Set with: security add-generic-password -U -a \"$USER\" -s \"<key>\" -w \"<value>\"")
        return 2
    print(f"  ✓ Credentials found in Keychain (from={user}, to={to_addr})")

    # 4. Send the test
    print()
    print("Sending test email…")
    result = send(plain)
    if result["ok"]:
        print(f"  ✓ Sent successfully — check your inbox at {to_addr}.")
        return 0
    else:
        print(f"  ❌ FAIL: {result['error']}")
        return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="HQ Watchdog email sender")
    parser.add_argument("--self-test", action="store_true", help="Run end-to-end self-test")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
