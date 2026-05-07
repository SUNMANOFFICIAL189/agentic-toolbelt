"""
Minimal Supabase REST client for PATS-Copy watchdog rules.

PostgREST query pattern. Read-only by design — runtime rules never write.
"""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from typing import Any

from .creds import supabase_creds


def _ssl_context() -> ssl.SSLContext:
    """SSL context that works on stock macOS Python (cert.pem path is broken).

    Mirrors the pattern in ~/claude-hq/watchdog/telegram.py and listener.py SSL fix
    (claude-hq commit 089a4b2). Prefer certifi when available — Python distros
    ship with it. Fall back to system context.
    """
    try:
        import certifi  # type: ignore[import-not-found]
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def query(table: str, *, select: str = "*", filters: dict[str, str] | None = None,
          order: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    """Run a PostgREST GET. Returns list of row dicts.

    filters: PostgREST query string fragments, e.g., {'status': 'eq.open'}.
    """
    url, key = supabase_creds()
    params: dict[str, str] = {"select": select}
    if filters:
        for k, v in filters.items():
            params[k] = v
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)

    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}?{qs}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


__all__ = ["query"]
