"""
Thin Paperclip REST API client used by the Paperclip watchdog runtime rules.

Read-only — never mutates Paperclip state. If Paperclip is down, every helper
returns None (or an empty list) and the calling rule decides whether that
itself constitutes a finding (typically server_health.py is the only rule
that treats Paperclip-being-down as the finding).

URL is read from PAPERCLIP_URL env var, defaulting to http://localhost:3100
which matches Paperclip's `pnpm dev` default and the AGENTS.md docs.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

PAPERCLIP_URL = os.environ.get("PAPERCLIP_URL", "http://localhost:3100").rstrip("/")
DEFAULT_TIMEOUT = 5  # seconds — short, this is a probe not a query


def _get(path: str, timeout: int = DEFAULT_TIMEOUT) -> Any | None:
    url = f"{PAPERCLIP_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def get_health() -> dict | None:
    """GET /health. Returns the response dict if alive, None if unreachable."""
    return _get("/health")


def is_server_alive() -> bool:
    """True if Paperclip's /health endpoint responded; False if unreachable."""
    return get_health() is not None


__all__ = ["PAPERCLIP_URL", "get_health", "is_server_alive"]
