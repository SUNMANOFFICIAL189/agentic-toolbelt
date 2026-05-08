#!/usr/bin/env python3
"""
Runtime rule: Healthchecks.io dead-man's switch relay.

Two pings each run:
  1. paperclip-server  — only sent if Paperclip /health responded
  2. paperclip-watchdog — always sent (the watchdog itself is alive iff this rule runs)

Healthchecks.io is configured (via the user's existing account) to send a
Telegram alert if either ping stops arriving. Silence is the alarm.

This rule never emits alert-grade Findings itself — it's a signal forwarder.
It does emit an info Finding when ping URLs are missing, so the operator
notices to set them up.

URL config (read from env):
    HC_PING_PAPERCLIP_SERVER     — Healthchecks.io URL for paperclip-server check
    HC_PING_PAPERCLIP_WATCHDOG   — Healthchecks.io URL for paperclip-watchdog check
Both fall back to reading ~/claude-hq/watchdog/healthchecks-urls.env if env unset.

Usage:
    python rules/runtime/healthchecks_io_relay.py
"""

from __future__ import annotations

import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

# macOS system Python doesn't always have its CA bundle linked to urllib
# (the "Install Certificates.command" step). certifi ships one we can point at.
try:
    import certifi  # type: ignore[import-not-found]
    _SSL_CONTEXT: ssl.SSLContext | None = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.finding import Finding, emit
from lib.paperclip_api import is_server_alive

RULE_ID = "paperclip-runtime-healthchecks-relay"
HC_URLS_FILE = Path.home() / "claude-hq" / "watchdog" / "healthchecks-urls.env"
PING_TIMEOUT = 5


def _read_url_from_env_file(key: str) -> str | None:
    """Lookup KEY=VALUE from healthchecks-urls.env (env-style file)."""
    if not HC_URLS_FILE.exists():
        return None
    try:
        for raw in HC_URLS_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                # Strip optional surrounding quotes
                v = v.strip().strip("'\"")
                return v or None
    except OSError:
        return None
    return None


def _resolve_url(env_key: str) -> str | None:
    return os.environ.get(env_key) or _read_url_from_env_file(env_key)


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=PING_TIMEOUT, context=_SSL_CONTEXT) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def main() -> int:
    server_url = _resolve_url("HC_PING_PAPERCLIP_SERVER")
    watchdog_url = _resolve_url("HC_PING_PAPERCLIP_WATCHDOG")

    if not server_url and not watchdog_url:
        emit(Finding(
            rule_id=f"{RULE_ID}.not-configured",
            severity="info",
            what_happened=(
                "The Paperclip watchdog is running but no Healthchecks.io ping URLs are "
                "configured yet. Without them, you won't get a Telegram alert if the "
                "watchdog itself silently dies."
            ),
            what_to_do=(
                "Create two checks in your Healthchecks.io account named 'paperclip-server' "
                "and 'paperclip-watchdog', then add their ping URLs to "
                "~/claude-hq/watchdog/healthchecks-urls.env as "
                "HC_PING_PAPERCLIP_SERVER=... and HC_PING_PAPERCLIP_WATCHDOG=..."
            ),
            technical_detail={
                "rule_id": f"{RULE_ID}.not-configured",
                "env_file_exists": HC_URLS_FILE.exists(),
            },
        ))
        return 0

    # Paperclip server ping — only sent if server actually responded
    if server_url:
        if is_server_alive():
            ok = _ping(server_url)
            if not ok:
                emit(Finding(
                    rule_id=f"{RULE_ID}.server-ping-failed",
                    severity="warn",
                    what_happened=(
                        "Paperclip is alive, but the watchdog couldn't reach Healthchecks.io "
                        "to confirm it. If this keeps happening, Healthchecks.io may eventually "
                        "alert that 'paperclip-server is down' even though it isn't."
                    ),
                    what_to_do=(
                        "Check your internet connection and that the URL in "
                        "healthchecks-urls.env for HC_PING_PAPERCLIP_SERVER is correct."
                    ),
                    technical_detail={
                        "rule_id": f"{RULE_ID}.server-ping-failed",
                        "url_redacted": server_url[:30] + "..." if len(server_url) > 30 else server_url,
                    },
                ))
        # If server is unreachable, server_health.py raises the alarm —
        # we deliberately do NOT ping HC.io here, so silence reaches HC.io
        # and triggers its own dead-man's-switch alert.

    # Watchdog self-ping — always sent (we got this far, we're alive)
    if watchdog_url:
        ok = _ping(watchdog_url)
        if not ok:
            emit(Finding(
                rule_id=f"{RULE_ID}.watchdog-ping-failed",
                severity="warn",
                what_happened=(
                    "The watchdog tried to tell Healthchecks.io 'I'm alive' and the call "
                    "didn't go through. Same risk as above — eventually HC.io may say "
                    "the watchdog is dead when it isn't."
                ),
                what_to_do=(
                    "Check the URL in healthchecks-urls.env for HC_PING_PAPERCLIP_WATCHDOG."
                ),
                technical_detail={
                    "rule_id": f"{RULE_ID}.watchdog-ping-failed",
                    "url_redacted": watchdog_url[:30] + "..." if len(watchdog_url) > 30 else watchdog_url,
                },
            ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
